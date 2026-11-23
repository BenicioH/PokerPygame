"""Componentes de interface: botão, controle deslizante, campo de texto e avisos."""

import pygame

from .. import config as C
from . import draw

STYLES = {
    "primary": (C.ACCENT, (70, 235, 130), (8, 30, 16)),
    "secondary": (C.PANEL_LIGHT, (52, 76, 94), C.TEXT),
    "danger": ((170, 50, 45), C.DANGER, C.TEXT),
    "warning": ((190, 130, 20), C.WARNING, (30, 20, 0)),
    "info": ((35, 110, 180), C.INFO, C.TEXT),
    "ghost": (C.BG, C.PANEL, C.TEXT_DIM),
}


def clipboard_get():
    """Texto da área de transferência, ou "" se não der para ler."""
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        return pygame.scrap.get_text() or ""
    except (pygame.error, AttributeError, NotImplementedError):
        return ""


class Button:
    """Botão clicável com efeito de hover e atalho de teclado opcional.

    Args:
        rect: posição e tamanho (``pygame.Rect`` ou tupla).
        label: texto do botão.
        on_click: função chamada sem argumentos quando o botão é clicado.
        style: chave de :data:`STYLES`.
        hotkey: tecla do pygame que também aciona o botão.
    """

    sound = None

    def __init__(self, rect, label, on_click, style="secondary", size=24, hotkey=None, enabled=True, sublabel=""):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.sublabel = sublabel
        self.on_click = on_click
        self.style = style
        self.size = size
        self.hotkey = hotkey
        self.enabled = enabled
        self.visible = True
        self.hover = 0.0
        self._pressed = False

    def handle_event(self, event):
        """Processa um evento. Devolve ``True`` se o botão o usou."""
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self._pressed = True
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                self.click()
                return True
        if event.type == pygame.KEYDOWN and self.hotkey is not None and event.key == self.hotkey:
            self.click()
            return True
        return False

    def click(self):
        """Executa a ação do botão."""
        if Button.sound:
            Button.sound.play("click")
        self.on_click()

    def update(self, dt):
        """Anima o hover."""
        target = 1.0 if self.enabled and self.rect.collidepoint(pygame.mouse.get_pos()) else 0.0
        self.hover += (target - self.hover) * min(1.0, dt * 14)

    def draw(self, surface):
        """Desenha o botão."""
        if not self.visible:
            return
        base, lit, fg = STYLES[self.style]
        color = draw.lerp_color(base, lit, self.hover) if self.enabled else (40, 52, 62)
        fg = fg if self.enabled else C.TEXT_FAINT
        rect = self.rect.move(0, 1 if self._pressed else 0)
        pygame.draw.rect(surface, (0, 0, 0), rect.move(0, 3), border_radius=10)
        pygame.draw.rect(surface, color, rect, border_radius=10)
        if self.sublabel:
            draw.text(surface, self.label, (rect.centerx, rect.centery - 9), self.size, fg, True, "center")
            draw.text(surface, self.sublabel, (rect.centerx, rect.centery + 12), 20, fg, False, "center")
        else:
            draw.text(surface, self.label, rect.center, self.size, fg, True, "center")


class Slider:
    """Controle deslizante horizontal para escolher um valor inteiro.

    Args:
        rect: área do trilho.
        minimum / maximum / value: faixa e valor inicial.
        step: o valor anda de ``step`` em ``step`` (o máximo sempre é alcançável).
    """

    def __init__(self, rect, minimum, maximum, value, step=1):
        self.rect = pygame.Rect(rect)
        self.step = max(1, step)
        self.dragging = False
        self.visible = True
        self.set_range(minimum, maximum, value)

    def set_range(self, minimum, maximum, value=None):
        """Muda a faixa (por exemplo, a cada vez que é a vez do jogador)."""
        self.minimum = minimum
        self.maximum = max(minimum, maximum)
        self.set_value(self.minimum if value is None else value)

    def set_value(self, value):
        """Ajusta o valor, respeitando a faixa e o passo."""
        value = max(self.minimum, min(self.maximum, int(value)))
        if value != self.maximum:
            value = self.minimum + round((value - self.minimum) / self.step) * self.step
            value = min(value, self.maximum)
        self.value = value

    def _value_at(self, x):
        """Valor correspondente à posição ``x`` do mouse no trilho."""
        t = (x - self.rect.left) / max(1, self.rect.width)
        return self.minimum + (self.maximum - self.minimum) * max(0.0, min(1.0, t))

    def handle_event(self, event):
        """Arrastar com o mouse ou girar a rodinha muda o valor."""
        if not self.visible:
            return False
        grab = self.rect.inflate(16, 24)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and grab.collidepoint(event.pos):
            self.dragging = True
            self.set_value(self._value_at(event.pos[0]))
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_value(self._value_at(event.pos[0]))
            return True
        if event.type == pygame.MOUSEWHEEL and grab.collidepoint(pygame.mouse.get_pos()):
            self.set_value(self.value + event.y * self.step)
            return True
        return False

    def draw(self, surface):
        """Trilho, parte preenchida e a bolinha."""
        if not self.visible:
            return
        r = self.rect
        pygame.draw.rect(surface, C.BG_DARK, r, border_radius=r.height // 2)
        span = self.maximum - self.minimum
        t = 1.0 if span == 0 else (self.value - self.minimum) / span
        fill = pygame.Rect(r.left, r.top, int(r.width * t), r.height)
        pygame.draw.rect(surface, C.ACCENT_DARK, fill, border_radius=r.height // 2)
        knob = (r.left + int(r.width * t), r.centery)
        pygame.draw.circle(surface, (0, 0, 0), (knob[0], knob[1] + 2), 11)
        pygame.draw.circle(surface, C.TEXT, knob, 11)
        pygame.draw.circle(surface, C.ACCENT, knob, 6)


class TextInput:
    """Campo de texto de uma linha (usado para o nome do jogador)."""

    def __init__(self, rect, value="", max_len=14):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.max_len = max_len
        self.focused = False
        self.blink = 0.0

    def handle_event(self, event):
        """Clique dá foco; teclas editam o texto."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focused = self.rect.collidepoint(event.pos)
            return self.focused
        if not self.focused:
            return False
        if event.type == pygame.TEXTINPUT:
            if len(self.value) < self.max_len:
                self.value += event.text[: self.max_len - len(self.value)]
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
                return True
            if event.key == pygame.K_v and event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
                pasted = clipboard_get()
                self.value = (self.value + pasted.strip())[: self.max_len]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.focused = False
                return True
        return False

    def update(self, dt):
        """Faz o cursor piscar."""
        self.blink = (self.blink + dt) % 1.0

    def draw(self, surface):
        """Caixa, texto e cursor."""
        draw.panel(surface, self.rect, C.BG_DARK, C.ACCENT if self.focused else C.PANEL_BORDER, 8)
        rect = draw.text(surface, self.value, (self.rect.left + 12, self.rect.centery), 28, C.TEXT, False, "midleft")
        if self.focused and self.blink < 0.5:
            x = rect.right + 2 if self.value else self.rect.left + 12
            pygame.draw.line(surface, C.TEXT, (x, self.rect.top + 10), (x, self.rect.bottom - 10), 2)


class Toasts:
    """Avisos curtos que aparecem no topo da tela e somem sozinhos."""

    def __init__(self):
        self.items = []

    def push(self, message, color=C.INFO, duration=2.6):
        """Mostra um aviso novo (no máximo 3 ao mesmo tempo)."""
        self.items.append([message, color, duration])
        self.items = self.items[-3:]

    def update(self, dt):
        """Conta o tempo e remove os avisos vencidos."""
        for item in self.items:
            item[2] -= dt
        self.items = [i for i in self.items if i[2] > 0]

    def draw(self, surface):
        """Desenha os avisos empilhados, sumindo no final."""
        y = 18
        for message, color, left in self.items:
            surf = draw.text_surface(message, 24, C.TEXT, True)
            rect = surf.get_rect(midtop=(C.WIDTH // 2, y)).inflate(36, 18)
            alpha = int(255 * min(1.0, left / 0.4))
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(layer, (*C.PANEL, 235), layer.get_rect(), border_radius=10)
            pygame.draw.rect(layer, (*color, 255), layer.get_rect(), 2, border_radius=10)
            layer.blit(surf, surf.get_rect(center=layer.get_rect().center))
            layer.set_alpha(alpha)
            surface.blit(layer, rect)
            y += rect.height + 8
