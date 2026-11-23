"""Menu de pausa aberto por cima da mesa (tecla Esc)."""

import pygame

from .. import config as C
from ..ui import draw
from ..ui.widgets import Button
from .base import Modal


class PauseScene(Modal):
    """Continuar, ligar/desligar sons, ver as regras ou sair da mesa."""

    def __init__(self, app, table):
        super().__init__(app, 420, 470, "Pausa")
        self.table = table
        self._build()

    def _build(self):
        """Cria os botões (de novo a cada troca de som, para atualizar os textos)."""
        r = self.rect
        x, w = r.left + 60, r.width - 120
        save = self.app.save
        leave_label = "Desistir do torneio" if self.table.session.mode == "tournament" else "Sair da mesa"
        self.buttons = [
            Button((x, r.top + 80, w, 54), "Continuar", self.close, "primary", 28, pygame.K_RETURN),
            Button((x, r.top + 146, w, 50), f"Música: {'ligada' if save['music'] else 'desligada'}", self._music, "secondary"),
            Button((x, r.top + 206, w, 50), f"Efeitos: {'ligados' if save['sfx'] else 'desligados'}", self._sfx, "secondary"),
            Button((x, r.top + 266, w, 50), "Como jogar", self._rules, "secondary"),
            Button((x, r.top + 356, w, 54), leave_label, self._leave, "danger", 26),
        ]

    def _music(self):
        """Liga ou desliga a música."""
        self.app.toggle_music()
        self._build()

    def _sfx(self):
        """Liga ou desliga os efeitos sonoros."""
        self.app.toggle_sfx()
        self._build()

    def _rules(self):
        """Abre o "Como jogar" por cima da pausa."""
        from .tutorial import TutorialScene
        self.app.push(TutorialScene(self.app, overlay=True))

    def _leave(self):
        """Fecha a pausa e pergunta se quer mesmo sair."""
        self.app.pop()
        self.table._ask_leave()

    def draw_body(self, surface, rect):
        """Dica da tecla Esc no rodapé."""
        draw.text(surface, "Esc para voltar", (rect.centerx, rect.bottom - 22), 19, C.TEXT_FAINT, False, "center")
