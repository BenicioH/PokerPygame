"""Tela inicial."""

import math

import pygame

from .. import config as C
from ..engine.cards import Card
from ..ui import draw
from ..ui.widgets import Button
from .base import Backdrop, Scene


class MenuScene(Scene):
    """Menu principal: jogar, como jogar, configurações e sair."""

    def __init__(self, app):
        super().__init__(app)
        self.backdrop = Backdrop()
        self.time = 0.0
        cx = C.WIDTH // 2
        items = [
            ("Jogar", self._play, "primary", pygame.K_RETURN),
            ("Como jogar", self._tutorial, "secondary", None),
            ("Configurações", self._settings, "secondary", None),
            ("Sair", self.app.quit, "ghost", None),
        ]
        self.buttons = [
            Button((cx - 160, 360 + i * 70, 320, 56), label, action, style, 28, hotkey)
            for i, (label, action, style, hotkey) in enumerate(items)
        ]
        self.cards = [Card(14, 0), Card(13, 1), Card(12, 2), Card(11, 3), Card(10, 0)]

    def _play(self):
        """Vai para o lobby."""
        from .lobby import LobbyScene
        self.app.replace(LobbyScene(self.app))

    def _tutorial(self):
        """Abre o "Como jogar"."""
        from .tutorial import TutorialScene
        self.app.replace(TutorialScene(self.app))

    def _settings(self):
        """Abre as configurações."""
        from .settings import SettingsScene
        self.app.replace(SettingsScene(self.app))

    def update(self, dt):
        """Anima o fundo e as cartas."""
        self.time += dt
        self.backdrop.update(dt)
        super().update(dt)

    def draw(self, surface):
        """Fundo, leque de cartas, título, saldo e botões."""
        self.backdrop.draw(surface)
        cx = C.WIDTH // 2
        for i, card in enumerate(self.cards):
            angle = (i - 2) * 9 + math.sin(self.time * 1.4 + i) * 2
            surf = pygame.transform.rotozoom(draw.card_surface(card, 70, 100), -angle, 1.0)
            x = cx + (i - 2) * 46
            y = 120 + abs(i - 2) * 8 + math.sin(self.time * 2 + i * 0.7) * 4
            surface.blit(surf, surf.get_rect(center=(x, y)))
        draw.text(surface, "POKER", (cx, 215), 96, C.TEXT, True, "midtop")
        draw.text(surface, "POWER-UP", (cx, 285), 52, C.ACCENT, True, "midtop")
        draw.text(surface, f"Saldo: {draw.format_chips(self.app.save['bankroll'])} fichas",
                  (C.WIDTH - 30, 30), 26, C.GOLD, True, "topright")
        draw.text(surface, f"Jogador: {self.app.save['name']}", (30, 30), 26, C.TEXT_DIM, False, "topleft")
        draw.text(surface, "F11: tela cheia", (cx, C.HEIGHT - 24), 20, C.TEXT_FAINT, False, "center")
        super().draw(surface)
