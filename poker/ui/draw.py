"""Funções de desenho reutilizadas por todas as telas.

Tudo é desenhado com formas simples do pygame (retângulos arredondados,
círculos e polígonos), inclusive os naipes das cartas. Superfícies que se
repetem muito (cartas, textos) ficam guardadas em cache para não serem
recriadas a cada quadro.
"""

import math

import pygame

from .. import config as C

_fonts = {}
_text_cache = {}
_card_cache = {}


def font(size, bold=False):
    """Fonte padrão do pygame no tamanho pedido (com cache)."""
    key = (size, bold)
    if key not in _fonts:
        f = pygame.font.Font(None, size)
        f.set_bold(bold)
        _fonts[key] = f
    return _fonts[key]


def text_surface(text, size, color=C.TEXT, bold=False):
    """Renderiza um texto (com cache, pois os mesmos textos aparecem sempre)."""
    key = (text, size, color, bold)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 600:
            _text_cache.clear()
        surf = font(size, bold).render(str(text), True, color)
        _text_cache[key] = surf
    return surf


def text(surface, value, pos, size=24, color=C.TEXT, bold=False, anchor="topleft"):
    """Desenha um texto. ``anchor`` é um atributo de ``Rect`` (``center``, ``midleft``...)."""
    surf = text_surface(value, size, color, bold)
    rect = surf.get_rect(**{anchor: pos})
    surface.blit(surf, rect)
    return rect


def wrap(value, size, width):
    """Quebra um texto em linhas que cabem em ``width`` pixels."""
    f = font(size)
    lines = []
    for paragraph in str(value).split("\n"):
        line = ""
        for word in paragraph.split(" "):
            test = f"{line} {word}".strip()
            if f.size(test)[0] <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def text_block(surface, value, rect, size=22, color=C.TEXT, spacing=4):
    """Desenha um parágrafo com quebra de linha dentro de ``rect``. Devolve a altura usada."""
    y = rect.top
    for line in wrap(value, size, rect.width):
        text(surface, line, (rect.left, y), size, color)
        y += font(size).get_linesize() + spacing
    return y - rect.top


def panel(surface, rect, color=C.PANEL, border=C.PANEL_BORDER, radius=12, width=2):
    """Retângulo arredondado com borda (fundo de painéis e botões)."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, width, border_radius=radius)


def alpha_rect(surface, rect, color, alpha, radius=0):
    """Retângulo semitransparente (escurecer o fundo de janelas)."""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (*color, alpha), layer.get_rect(), border_radius=radius)
    surface.blit(layer, rect.topleft)


def lerp_color(a, b, t):
    """Mistura duas cores (``t`` de 0 a 1)."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def suit_shape(surface, suit, center, size, color):
    """Desenha o símbolo de um naipe com formas geométricas.

    Args:
        suit: 0 espadas, 1 copas, 2 ouros, 3 paus.
        center: centro do símbolo.
        size: altura aproximada em pixels.
    """
    x, y = center
    s = size / 2
    if suit == 2:
        pygame.draw.polygon(surface, color, [(x, y - s), (x + s * 0.75, y), (x, y + s), (x - s * 0.75, y)])
    elif suit == 1:
        r = s * 0.52
        pygame.draw.circle(surface, color, (int(x - r * 0.9), int(y - s * 0.3)), int(r))
        pygame.draw.circle(surface, color, (int(x + r * 0.9), int(y - s * 0.3)), int(r))
        pygame.draw.polygon(surface, color, [(x - s * 0.98, y - s * 0.15), (x + s * 0.98, y - s * 0.15), (x, y + s)])
    elif suit == 0:
        r = s * 0.5
        pygame.draw.circle(surface, color, (int(x - r * 0.9), int(y + s * 0.2)), int(r))
        pygame.draw.circle(surface, color, (int(x + r * 0.9), int(y + s * 0.2)), int(r))
        pygame.draw.polygon(surface, color, [(x - s * 0.95, y + s * 0.05), (x + s * 0.95, y + s * 0.05), (x, y - s)])
        pygame.draw.polygon(surface, color, [(x, y + s * 0.2), (x - s * 0.4, y + s), (x + s * 0.4, y + s)])
    else:
        r = s * 0.42
        pygame.draw.circle(surface, color, (int(x), int(y - s * 0.45)), int(r))
        pygame.draw.circle(surface, color, (int(x - s * 0.5), int(y + s * 0.1)), int(r))
        pygame.draw.circle(surface, color, (int(x + s * 0.5), int(y + s * 0.1)), int(r))
        pygame.draw.polygon(surface, color, [(x, y), (x - s * 0.4, y + s), (x + s * 0.4, y + s)])


def card_surface(card, w, h, face_up=True):
    """Superfície de uma carta (frente ou verso), com cache por tamanho."""
    key = (card.rank if card and face_up else 0, card.suit if card and face_up else 0, w, h, face_up)
    if key in _card_cache:
        return _card_cache[key]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rect = surf.get_rect()
    radius = max(4, w // 9)
    if face_up and card is not None:
        pygame.draw.rect(surf, C.CARD_FACE, rect, border_radius=radius)
        pygame.draw.rect(surf, (200, 200, 195), rect, 1, border_radius=radius)
        color = C.CARD_RED if card.is_red else C.CARD_BLACK
        label = font(int(h * 0.42), True).render(card.rank_label, True, color)
        surf.blit(label, label.get_rect(topleft=(int(w * 0.1), int(h * 0.06))))
        suit_shape(surf, card.suit, (w * 0.25, h * 0.55), h * 0.17, color)
        suit_shape(surf, card.suit, (w * 0.62, h * 0.7), h * 0.42, color)
    else:
        pygame.draw.rect(surf, C.CARD_BACK, rect, border_radius=radius)
        inner = rect.inflate(-w * 0.18, -w * 0.18)
        pygame.draw.rect(surf, C.CARD_BACK_LINE, inner, 2, border_radius=radius)
        for i in range(-h, w, max(6, w // 6)):
            pygame.draw.line(surf, C.CARD_BACK_LINE, (inner.left + i, inner.top), (inner.left + i + inner.height, inner.bottom), 1)
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), rect, border_radius=radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(surf, (230, 235, 255), rect, 2, border_radius=radius)
    _card_cache[key] = surf
    return surf


def draw_card(surface, card, center, w, h, face_up=True, flip=1.0, alpha=255, highlight=None):
    """Desenha uma carta centrada em ``center``.

    Args:
        flip: largura relativa de 0 a 1, usada para a animação de virar.
        highlight: cor de um contorno extra (carta vencedora, carta escolhida...).
    """
    surf = card_surface(card, w, h, face_up)
    if flip < 1.0:
        surf = pygame.transform.smoothscale(surf, (max(1, int(w * flip)), h))
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(alpha)
    shadow = pygame.Rect(0, 0, surf.get_width(), h)
    shadow.center = (center[0] + 2, center[1] + 3)
    alpha_rect(surface, shadow, (0, 0, 0), min(alpha, 70), radius=max(4, w // 9))
    rect = surf.get_rect(center=center)
    surface.blit(surf, rect)
    if highlight:
        pygame.draw.rect(surface, highlight, rect.inflate(6, 6), 3, border_radius=max(6, w // 7))
    return rect


def card_slot(surface, center, w, h):
    """Contorno de um espaço vazio para carta (cartas da mesa ainda fechadas)."""
    rect = pygame.Rect(0, 0, w, h)
    rect.center = center
    pygame.draw.rect(surface, C.FELT_DARK, rect, border_radius=max(4, w // 9))
    pygame.draw.rect(surface, (40, 135, 92), rect, 2, border_radius=max(4, w // 9))


def powerup_icon(surface, pu, center, radius, enabled=True):
    """Ícone de um power-up: círculo na cor da raridade com o símbolo (cinza se não der para usar)."""
    color = pu.color if enabled else (70, 80, 90)
    pygame.draw.circle(surface, (0, 0, 0), (center[0], center[1] + 2), radius)
    pygame.draw.circle(surface, lerp_color(color, C.BG, 0.55), center, radius)
    pygame.draw.circle(surface, color, center, radius, 3)
    text(surface, pu.symbol, center, int(radius * 1.1), color, True, "center")


CHIP_COLORS = [
    (1000, (240, 190, 50)),
    (100, (30, 30, 30)),
    (25, (40, 150, 70)),
    (5, (200, 50, 50)),
    (1, (230, 230, 230)),
]


def chip(surface, center, color, radius=10):
    """Uma ficha vista de cima, com as listras da borda."""
    x, y = int(center[0]), int(center[1])
    pygame.draw.circle(surface, (0, 0, 0), (x + 1, y + 2), radius)
    pygame.draw.circle(surface, color, (x, y), radius)
    stripe = (250, 250, 250) if sum(color) < 600 else (60, 60, 60)
    for k in range(6):
        a = k * math.pi / 3
        px = x + math.cos(a) * radius * 0.78
        py = y + math.sin(a) * radius * 0.78
        pygame.draw.circle(surface, stripe, (int(px), int(py)), max(1, radius // 5))
    pygame.draw.circle(surface, stripe, (x, y), int(radius * 0.55), 1)


def chip_stack(surface, center, amount, radius=10, max_chips=6):
    """Pilha de fichas que representa ``amount`` (as cores seguem o valor)."""
    if amount <= 0:
        return
    chips = []
    rest = amount
    for value, color in CHIP_COLORS:
        while rest >= value and len(chips) < max_chips:
            chips.append(color)
            rest -= value
    if not chips:
        chips = [CHIP_COLORS[-1][1]]
    x, y = center
    for i, color in enumerate(reversed(chips)):
        chip(surface, (x, y - i * 3), color, radius)


def format_chips(amount):
    """Formata fichas com separador de milhar: 12500 -> ``12.500``."""
    return f"{int(amount):,}".replace(",", ".")
