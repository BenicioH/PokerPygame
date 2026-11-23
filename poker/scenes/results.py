"""Tela de fim de jogo (saída do cash ou fim do torneio)."""

import pygame

from .. import config as C
from ..ui import draw
from ..ui.effects import Particles
from ..ui.widgets import Button
from .base import Backdrop, Scene


class ResultsScene(Scene):
    """Resumo da sessão com o lucro ou prejuízo.

    Args:
        title: título grande (por exemplo "Campeão!").
        lines: lista de ``(rótulo, valor)`` para a tabela de estatísticas.
        profit: ganho (positivo) ou perda (negativa) em fichas.
    """

    def __init__(self, app, title, lines, profit):
        super().__init__(app)
        self.title = title
        self.lines = lines
        self.profit = profit
        self.backdrop = Backdrop(seed=21)
        self.particles = Particles()
        self.next_confetti = 1.0
        cx = C.WIDTH // 2
        self.buttons = [
            Button((cx - 270, 600, 250, 58), "Voltar ao lobby", self._lobby, "primary", 26, pygame.K_RETURN),
            Button((cx + 20, 600, 250, 58), "Menu principal", self._menu, "secondary", 26, pygame.K_ESCAPE),
        ]

    def _lobby(self):
        """Volta ao lobby."""
        from .lobby import LobbyScene
        self.app.replace(LobbyScene(self.app))

    def _menu(self):
        """Volta ao menu principal."""
        from .menu import MenuScene
        self.app.replace(MenuScene(self.app))

    def update(self, dt):
        """Anima o fundo e solta confete a cada segundo se o resultado foi positivo."""
        super().update(dt)
        self.backdrop.update(dt)
        self.particles.update(dt)
        if self.profit > 0:
            self.next_confetti -= dt
            if self.next_confetti <= 0:
                self.next_confetti += 1.0
                self.particles.burst((C.WIDTH // 2, 140), [C.GOLD, C.ACCENT, (255, 255, 255)], 40, 300)

    def draw(self, surface):
        """Título, resultado em fichas, tabela de estatísticas e saldo."""
        self.backdrop.draw(surface)
        cx = C.WIDTH // 2
        draw.text(surface, self.title, (cx, 110), 64, C.GOLD if self.profit > 0 else C.TEXT, True, "center")
        if self.profit > 0:
            sign, color = "+", C.ACCENT
        elif self.profit < 0:
            sign, color = "-", C.DANGER
        else:
            sign, color = "", C.TEXT_DIM
        draw.text(surface, f"Resultado: {sign}{draw.format_chips(abs(self.profit))} fichas", (cx, 178), 34, color, True, "center")
        box = pygame.Rect(cx - 280, 228, 560, 52 * len(self.lines) + 24)
        draw.panel(surface, box, C.PANEL, C.PANEL_BORDER, 14)
        for i, (label, value) in enumerate(self.lines):
            y = box.top + 38 + i * 52
            draw.text(surface, label, (box.left + 30, y), 28, C.TEXT_DIM, False, "midleft")
            draw.text(surface, value, (box.right - 30, y), 30, C.TEXT, True, "midright")
        draw.text(surface, f"Saldo: {draw.format_chips(self.app.save['bankroll'])}", (cx, 568), 26, C.GOLD, True, "center")
        self.particles.draw(surface)
        super().draw(surface)
