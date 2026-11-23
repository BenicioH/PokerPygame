"""Roleta de power-ups, aberta a cada 3 mãos por cima da mesa."""

import math
import random

import pygame

from .. import config as C
from ..ui import draw
from ..ui.widgets import Button
from .base import Scene

SPIN_TIME = 4.5
RADIUS = 200


def ease_out_quart(t):
    """Desaceleração forte no fim, como uma roleta de verdade."""
    return 1 - (1 - t) ** 4


class LocalRoulette:
    """Controle da roleta no jogo contra bots: tudo acontece neste computador."""

    def __init__(self, session):
        self.session = session
        self.roulette = session.make_roulette()
        self.result = None
        self.closed = False
        self.version = 0

    def stack(self):
        """Fichas do jogador na mesa."""
        return self.session.human.stack

    def removal_cost(self, key):
        """Quanto custa tirar um power-up da roleta."""
        return self.roulette.removal_cost(key)

    def can_remove(self, key):
        """Se dá para tirar o power-up (sobra mais de um e há fichas)."""
        return self.roulette.can_remove(key, self.stack())

    def remove(self, key):
        """Paga e tira o power-up. Devolve se deu certo."""
        if self.session.pay_removal(self.roulette, key):
            self.version += 1
            return True
        return False

    def spin(self):
        """Sorteia o resultado na hora."""
        self.result = self.roulette.spin()

    def finish(self):
        """Entrega o power-up sorteado ao jogador."""
        self.session.grant(self.result)

    def seconds_left(self):
        """No jogo local a roleta espera o jogador: sem tempo limite."""
        return None


class RouletteScene(Scene):
    """Mostra a roleta, deixa remover power-ups pagando e gira.

    Args:
        control: :class:`LocalRoulette`.
        on_done: função chamada quando a janela fecha (começa a próxima mão).
    """

    overlay = True

    def __init__(self, app, control, on_done):
        super().__init__(app)
        self.control = control
        self.on_done = on_done
        self.roulette = control.roulette
        self.seen_version = control.version
        self.rect = pygame.Rect(0, 0, 1080, 610)
        self.rect.center = (C.WIDTH // 2, C.HEIGHT // 2)
        self.center = (self.rect.left + 270, self.rect.top + 330)
        self.angle = random.uniform(0, 360)
        self.phase = "choose"
        self.time = 0.0
        self.result = None
        self.appear = 0.0
        self.last_segment = None
        self.glow = 0.0
        self._render_wheel()
        self._build_buttons()

    def _segments(self):
        """Lista ``(power-up, ângulo_inicial, ângulo_final)`` em graus."""
        active = self.roulette.active
        total = sum(p.weight for p in active)
        out = []
        start = 0.0
        for p in active:
            span = 360.0 * p.weight / total
            out.append((p, start, start + span))
            start += span
        return out

    def _render_wheel(self):
        """Desenha a roleta (sem rotação) em uma superfície guardada."""
        size = RADIUS * 2 + 8
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        for i, (p, a0, a1) in enumerate(self._segments()):
            shade = 0.25 if i % 2 else 0.4
            color = draw.lerp_color(p.color, C.BG_DARK, shade)
            points = [(c, c)]
            steps = max(2, int((a1 - a0) / 3))
            for k in range(steps + 1):
                a = math.radians(a0 + (a1 - a0) * k / steps)
                points.append((c + math.cos(a) * RADIUS, c - math.sin(a) * RADIUS))
            pygame.draw.polygon(surf, color, points)
            pygame.draw.line(surf, C.BG_DARK, (c, c), points[1], 3)
            mid = math.radians((a0 + a1) / 2)
            sx, sy = c + math.cos(mid) * RADIUS * 0.7, c - math.sin(mid) * RADIUS * 0.7
            label = draw.text_surface(p.symbol, 34 if a1 - a0 > 20 else 24, C.TEXT, True)
            label = pygame.transform.rotate(label, math.degrees(mid) - 90)
            surf.blit(label, label.get_rect(center=(sx, sy)))
        pygame.draw.circle(surf, C.RIM_LIGHT, (c, c), RADIUS, 6)
        pygame.draw.circle(surf, C.PANEL, (c, c), 34)
        pygame.draw.circle(surf, C.GOLD, (c, c), 34, 4)
        self.wheel = surf

    def _build_buttons(self):
        """Botões "Remover" e "GIRAR!" na escolha; "Continuar" no resultado."""
        self.buttons = []
        if self.phase == "choose":
            x = self.rect.left + 540
            for i, p in enumerate(self.roulette.entries):
                if p.key not in self.roulette.removed:
                    label = f"Remover {draw.format_chips(self.control.removal_cost(p.key))}"
                    self.buttons.append(Button((x + 360, self.rect.top + 118 + i * 56, 140, 40), label,
                                               lambda k=p.key: self._remove(k), "danger", 22,
                                               enabled=self.control.can_remove(p.key)))
            self.buttons.append(Button((self.rect.left + 600, self.rect.bottom - 86, 380, 62), "GIRAR!", self._spin,
                                       "primary", 34, pygame.K_SPACE))
        elif self.phase == "result":
            self.buttons.append(Button((self.rect.centerx - 130, self.rect.bottom - 86, 260, 60), "Continuar",
                                       self._close, "primary", 30, pygame.K_RETURN))

    def _remove(self, key):
        """Botão "Remover" de um power-up."""
        if self.control.remove(key):
            self.app.sound.play("chip")

    def _spin(self):
        """Botão "GIRAR!": pede o sorteio e espera o resultado."""
        if self.phase != "choose":
            return
        self.phase = "waiting"
        self.buttons = []
        self.control.spin()

    def _start_spin(self):
        """O resultado já é conhecido: calcula o ângulo final e começa a girar."""
        self.phase = "spinning"
        self.result = self.control.result
        target = 0.0
        for p, a0, a1 in self._segments():
            if p is self.result:
                target = a0 + (a1 - a0) * random.uniform(0.2, 0.8)
                break
        delta = (90 - target - self.angle) % 360 + 360 * 5
        self.spin_from = self.angle
        self.spin_delta = delta
        self.time = 0.0

    def _close(self):
        """Botão "Continuar": entrega o prêmio e fecha a roleta."""
        self.control.finish()
        self.app.pop()
        self.on_done()

    def _segment_at_pointer(self):
        """Índice da fatia que está sob o ponteiro agora."""
        theta = (90 - self.angle) % 360
        for i, (_, a0, a1) in enumerate(self._segments()):
            if a0 <= theta < a1:
                return i
        return None

    def update(self, dt):
        """Acompanha o controle (mudanças, sorteio, tempo esgotado) e anima o giro."""
        super().update(dt)
        self.appear = min(1.0, self.appear + dt * 5)
        self.glow += dt
        if self.control.version != self.seen_version:
            self.seen_version = self.control.version
            self._render_wheel()
            if self.phase == "choose":
                self._build_buttons()
        if self.control.closed and self.phase in ("choose", "waiting"):
            self.app.toasts.push(f"Roleta: você ganhou {self.control.result.name}!", self.control.result.color)
            self.app.pop()
            self.on_done()
            return
        if self.phase == "waiting" and self.control.result is not None:
            self._start_spin()
        if self.phase == "spinning":
            self.time += dt
            t = min(1.0, self.time / SPIN_TIME)
            self.angle = self.spin_from + self.spin_delta * ease_out_quart(t)
            segment = self._segment_at_pointer()
            if segment != self.last_segment:
                self.last_segment = segment
                self.app.sound.play("tick")
            if t >= 1.0:
                self.phase = "result"
                self.app.sound.play("reward")
                self._build_buttons()

    def draw(self, surface):
        """Janela, roleta com o ponteiro e, ao lado, a lista de chances ou o prêmio."""
        draw.alpha_rect(surface, surface.get_rect(), (0, 0, 0), int(170 * self.appear))
        r = self.rect
        draw.panel(surface, r, C.PANEL, C.GOLD, 18, 3)
        draw.text(surface, "Roleta de Power-ups", (r.centerx, r.top + 36), 42, C.GOLD, True, "center")

        rotated = pygame.transform.rotozoom(self.wheel, self.angle, 1.0)
        surface.blit(rotated, rotated.get_rect(center=self.center))
        cx, cy = self.center
        tip = (cx, cy - RADIUS + 18)
        pygame.draw.polygon(surface, (0, 0, 0), [(tip[0] - 18, tip[1] - 38), (tip[0] + 18, tip[1] - 38), (tip[0], tip[1] + 4)])
        pygame.draw.polygon(surface, C.TEXT, [(tip[0] - 15, tip[1] - 36), (tip[0] + 15, tip[1] - 36), tip])
        draw.text(surface, "?", self.center, 40, C.GOLD, True, "center")

        if self.phase == "result":
            self._draw_result(surface)
        else:
            self._draw_list(surface)
        super().draw(surface)

    def _draw_list(self, surface):
        """Lista de power-ups com a chance de cada um."""
        r = self.rect
        x = r.left + 540
        draw.text(surface, "Chance de cada power-up", (x, r.top + 80), 24, C.TEXT, True)
        probs = self.roulette.probabilities()
        for i, p in enumerate(self.roulette.entries):
            y = r.top + 118 + i * 56
            removed = p.key not in probs
            draw.powerup_icon(surface, p, (x + 20, y + 20), 18, not removed)
            color = C.TEXT_FAINT if removed else C.TEXT
            draw.text(surface, p.name, (x + 48, y + 2), 24, color, True)
            draw.text(surface, p.rarity[0], (x + 48, y + 24), 19, C.TEXT_FAINT if removed else p.color)
            chance = "removido" if removed else f"{probs[p.key]:.0%}"
            draw.text(surface, chance, (x + 340, y + 20), 26, color, True, "midright")
        draw.text(surface, f"Suas fichas: {draw.format_chips(self.control.stack())}  •  quanto maior a chance, mais caro remover",
                  (x, r.bottom - 112), 19, C.TEXT_DIM)
        left = self.control.seconds_left()
        if left is not None:
            draw.text(surface, f"Gira sozinha em {left}s", (r.right - 30, r.top + 36), 22, C.WARNING, True, "midright")

    def _draw_result(self, surface):
        """Cartão do power-up ganho, com a borda pulsando."""
        p = self.result
        r = self.rect
        card = pygame.Rect(r.left + 560, r.top + 110, 460, 360)
        pulse = 0.5 + 0.5 * math.sin(self.glow * 4)
        draw.panel(surface, card, C.BG_DARK, draw.lerp_color(p.color, C.TEXT, pulse * 0.4), 16, 4)
        draw.text(surface, "Você ganhou", (card.centerx, card.top + 34), 26, C.TEXT_DIM, False, "center")
        draw.powerup_icon(surface, p, (card.centerx, card.top + 112), 48)
        draw.text(surface, p.name, (card.centerx, card.top + 190), 40, p.color, True, "center")
        draw.text(surface, p.rarity[0], (card.centerx, card.top + 224), 24, C.TEXT_DIM, False, "center")
        draw.text_block(surface, p.description, pygame.Rect(card.left + 30, card.top + 254, card.width - 60, 100), 22, C.TEXT)
