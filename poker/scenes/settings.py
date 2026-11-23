"""Configurações: nome do jogador, som e reinício do progresso."""

import pygame

from .. import config as C
from ..storage import DEFAULTS
from ..ui import draw
from ..ui.widgets import Button, TextInput
from .base import Backdrop, ConfirmDialog, Scene


class SettingsScene(Scene):
    """Ajustes salvos no ``data/save.json``."""

    def __init__(self, app):
        super().__init__(app)
        self.backdrop = Backdrop(seed=13)
        self.name_input = TextInput((C.WIDTH // 2 - 60, 190, 320, 50), app.save["name"])
        self._build()

    def _build(self):
        """Cria os botões (de novo a cada troca, para atualizar textos e cores)."""
        save = self.app.save
        x = C.WIDTH // 2 - 60
        self.buttons = [
            Button((30, 24, 130, 44), "< Menu", self._back, "ghost", 24),
            Button((x, 270, 320, 50), "Ligada" if save["music"] else "Desligada", self._music,
                   "primary" if save["music"] else "secondary"),
            Button((x, 340, 320, 50), "Ligados" if save["sfx"] else "Desligados", self._sfx,
                   "primary" if save["sfx"] else "secondary"),
            Button((x, 450, 320, 50), "Apagar progresso", self._ask_reset, "danger"),
        ]

    def _back(self):
        """Guarda o nome e volta ao menu."""
        self._save_name()
        from .menu import MenuScene
        self.app.replace(MenuScene(self.app))

    def _save_name(self):
        """Guarda o nome digitado (um nome vazio é ignorado)."""
        name = self.name_input.value.strip()
        if name:
            self.app.save["name"] = name

    def _music(self):
        """Liga ou desliga a música."""
        self.app.toggle_music()
        self._build()

    def _sfx(self):
        """Liga ou desliga os efeitos sonoros."""
        self.app.toggle_sfx()
        self._build()

    def _ask_reset(self):
        """Pede confirmação antes de apagar o progresso."""
        self.app.push(ConfirmDialog(self.app, "Apagar progresso?",
                                    "Saldo, estatísticas e power-ups guardados voltam ao início.", self._reset, "Apagar"))

    def _reset(self):
        """Volta tudo ao início, mas mantém o nome e as escolhas de som."""
        save = self.app.save
        keep = {"name": save["name"], "music": save["music"], "sfx": save["sfx"]}
        save.data = dict(DEFAULTS, **keep)
        save.save()
        self.app.toasts.push("Progresso apagado.", C.WARNING)

    def handle_event(self, event):
        """Esc volta (se não estiver digitando); o campo de nome vem antes dos botões."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.name_input.focused:
            self._back()
            return True
        if self.name_input.handle_event(event):
            if not self.name_input.focused:
                self._save_name()
            return True
        return super().handle_event(event)

    def update(self, dt):
        """Anima o fundo e o cursor do campo de nome."""
        self.backdrop.update(dt)
        self.name_input.update(dt)
        super().update(dt)

    def on_quit(self):
        """Fechar a janela também guarda o nome."""
        self._save_name()

    def draw(self, surface):
        """Rótulos à esquerda dos botões e as estatísticas no rodapé."""
        self.backdrop.draw(surface)
        draw.text(surface, "Configurações", (C.WIDTH // 2, 80), 52, C.TEXT, True, "center")
        x = C.WIDTH // 2 - 90
        for y, label in ((215, "Seu nome"), (295, "Música"), (365, "Efeitos sonoros"), (475, "Progresso")):
            draw.text(surface, label, (x, y), 28, C.TEXT_DIM, False, "midright")
        self.name_input.draw(surface)
        save = self.app.save
        stats = (f"Mãos jogadas: {save['hands_played']}   •   Torneios vencidos: {save['tournaments_won']}"
                 f"   •   Maior saque: {draw.format_chips(save['best_cashout'])}")
        draw.text(surface, stats, (C.WIDTH // 2, 580), 24, C.TEXT_DIM, False, "center")
        super().draw(surface)
