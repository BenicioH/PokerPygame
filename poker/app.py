"""Janela principal, laço do jogo e pilha de cenas."""

import pygame

from . import config as C
from .storage import SaveData
from .ui import draw
from .ui.sound import SoundManager
from .ui.widgets import Button, Toasts


def make_icon():
    """Ícone da janela: um naipe de espadas verde."""
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(icon, C.BG, icon.get_rect(), border_radius=6)
    draw.suit_shape(icon, 0, (16, 16), 22, C.ACCENT)
    return icon


class App:
    """O jogo inteiro: cria a janela, guarda os serviços e roda o laço principal.

    Serviços disponíveis para as cenas:
        ``app.save`` (jogo salvo), ``app.sound`` (sons) e ``app.toasts`` (avisos).
    """

    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(C.TITLE)
        pygame.display.set_icon(make_icon())
        self.screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.save = SaveData()
        self.sound = SoundManager(self.save["sfx"], self.save["music"])
        Button.sound = self.sound
        self.toasts = Toasts()
        self.stack = []
        self.running = True

    @property
    def top(self):
        """Cena ativa."""
        return self.stack[-1] if self.stack else None

    def push(self, scene):
        """Abre uma cena por cima da atual."""
        self.stack.append(scene)

    def pop(self):
        """Fecha a cena do topo (a de baixo volta a receber eventos)."""
        self.stack.pop()

    def replace(self, scene):
        """Troca todas as cenas por ``scene`` (navegação entre telas principais)."""
        self.stack = [scene]

    def toggle_music(self):
        """Liga ou desliga a música e guarda a escolha."""
        self.save["music"] = not self.save["music"]
        self.sound.set_music(self.save["music"])

    def toggle_sfx(self):
        """Liga ou desliga os efeitos sonoros e guarda a escolha."""
        self.save["sfx"] = not self.save["sfx"]
        self.sound.set_sfx(self.save["sfx"])

    def run(self, first_scene):
        """Roda o jogo até a janela fechar."""
        self.replace(first_scene)
        self.sound.start_music()
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif self.top:
                    self.top.handle_event(event)
            if not self.running:
                break
            if self.top:
                self.top.update(dt)
            self.toasts.update(dt)
            self._draw()
        pygame.quit()

    def _draw(self):
        """Desenha a cena do topo e, se ela for sobreposta, as de baixo também."""
        first = len(self.stack) - 1
        while first > 0 and self.stack[first].overlay:
            first -= 1
        for scene in self.stack[first:]:
            scene.draw(self.screen)
        self.toasts.draw(self.screen)
        pygame.display.flip()

    def quit(self):
        """Avisa as cenas abertas (para salvarem) e encerra."""
        for scene in reversed(self.stack):
            scene.on_quit()
        self.save.save()
        self.running = False
