"""Classe base das telas (cenas) e o fundo animado comum."""

import math
import random

import pygame

from .. import config as C
from ..ui import draw
from ..ui.widgets import Button


class Scene:
    """Uma tela do jogo.

    O :class:`~poker.app.App` mantém uma pilha de cenas. Só a cena do topo
    recebe eventos e é atualizada. Cenas com ``overlay = True`` (janelas,
    pausa, roleta) são desenhadas por cima da cena de baixo.
    """

    overlay = False

    def __init__(self, app):
        self.app = app
        self.buttons = []

    def handle_event(self, event):
        """Repassa o evento aos botões. Devolve ``True`` se algum o usou."""
        for button in list(self.buttons):
            if button.handle_event(event):
                return True
        return False

    def update(self, dt):
        """Atualiza animações (``dt`` em segundos)."""
        for button in self.buttons:
            button.update(dt)

    def draw(self, surface):
        """Desenha a cena."""
        for button in self.buttons:
            button.draw(surface)

    def on_quit(self):
        """Chamado quando o jogo fecha com esta cena aberta (para salvar)."""


class Backdrop:
    """Fundo com naipes flutuando devagar, usado no menu e no lobby."""

    def __init__(self, count=26, seed=3):
        rng = random.Random(seed)
        self.items = [
            [rng.uniform(0, C.WIDTH), rng.uniform(0, C.HEIGHT), rng.uniform(14, 46),
             rng.randrange(4), rng.uniform(8, 22), rng.uniform(0, math.tau)]
            for _ in range(count)
        ]
        self.time = 0.0

    def update(self, dt):
        """Sobe os naipes e os traz de volta por baixo da tela."""
        self.time += dt
        for item in self.items:
            item[1] -= item[4] * dt
            if item[1] < -50:
                item[1] = C.HEIGHT + 50

    def draw(self, surface):
        """Pinta o fundo e os naipes com balanço lateral."""
        surface.fill(C.BG)
        for x, y, size, suit, _, phase in self.items:
            sway = math.sin(self.time * 0.6 + phase) * 12
            color = (32, 50, 64) if suit in (0, 3) else (48, 40, 56)
            draw.suit_shape(surface, suit, (x + sway, y), size, color)


class Modal(Scene):
    """Janela no centro da tela com fundo escurecido."""

    overlay = True

    def __init__(self, app, width, height, title):
        super().__init__(app)
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (C.WIDTH // 2, C.HEIGHT // 2)
        self.title = title
        self.appear = 0.0

    def handle_event(self, event):
        """Esc fecha a janela."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return super().handle_event(event)

    def close(self):
        """Fecha a janela."""
        self.app.pop()

    def update(self, dt):
        """Anima a entrada da janela."""
        self.appear = min(1.0, self.appear + dt * 6)
        super().update(dt)

    def draw(self, surface):
        """Fundo escurecido, painel deslizando para o lugar, título e conteúdo."""
        draw.alpha_rect(surface, surface.get_rect(), (0, 0, 0), int(160 * self.appear))
        offset = int((1 - self.appear) * 30)
        rect = self.rect.move(0, offset)
        draw.panel(surface, rect, C.PANEL, C.PANEL_BORDER, 16)
        draw.text(surface, self.title, (rect.centerx, rect.top + 34), 38, C.TEXT, True, "center")
        self.draw_body(surface, rect)
        super().draw(surface)

    def draw_body(self, surface, rect):
        """Conteúdo da janela (as subclasses desenham aqui)."""


class ConfirmDialog(Modal):
    """Pergunta de sim ou não."""

    def __init__(self, app, title, message, on_yes, yes_label="Sim", danger=True, on_no=None, no_label="Cancelar"):
        super().__init__(app, 520, 260, title)
        self.message = message
        self.on_yes = on_yes
        self.on_no = on_no
        r = self.rect
        self.buttons = [
            Button((r.left + 40, r.bottom - 80, 200, 52), no_label, self.close, "secondary"),
            Button((r.right - 240, r.bottom - 80, 200, 52), yes_label, self._yes, "danger" if danger else "primary",
                   hotkey=pygame.K_RETURN),
        ]

    def close(self):
        """Cancelar: fecha e, se houver, chama ``on_no``."""
        self.app.pop()
        if self.on_no:
            self.on_no()

    def _yes(self):
        """Confirmar: fecha e chama ``on_yes``."""
        self.app.pop()
        self.on_yes()

    def draw_body(self, surface, rect):
        """A pergunta."""
        draw.text_block(surface, self.message, pygame.Rect(rect.left + 40, rect.top + 72, rect.width - 80, 100), 24, C.TEXT_DIM)
