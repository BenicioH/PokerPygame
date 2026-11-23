"""Tela "Como jogar": regras do poker, ranking das mãos e power-ups."""

import pygame

from .. import config as C
from ..engine.cards import Card
from ..engine.powerups import ALL_POWERUPS, MAX_INVENTORY, SPIN_EVERY
from ..ui import draw
from ..ui.widgets import Button
from .base import Backdrop, Scene

HAND_EXAMPLES = [
    ("Straight flush", [(9, 1), (10, 1), (11, 1), (12, 1), (13, 1)]),
    ("Quadra", [(8, 0), (8, 1), (8, 2), (8, 3), (13, 0)]),
    ("Full house", [(12, 0), (12, 1), (12, 2), (5, 3), (5, 1)]),
    ("Flush", [(2, 2), (6, 2), (9, 2), (11, 2), (14, 2)]),
    ("Sequência", [(5, 0), (6, 1), (7, 3), (8, 2), (9, 0)]),
    ("Trinca", [(7, 0), (7, 1), (7, 3), (12, 2), (3, 0)]),
    ("Dois pares", [(11, 0), (11, 2), (4, 1), (4, 3), (14, 0)]),
    ("Par", [(10, 1), (10, 3), (2, 0), (7, 2), (13, 1)]),
    ("Carta alta", [(14, 3), (9, 1), (6, 0), (4, 2), (2, 1)]),
]

PAGES = [
    ("O jogo", [
        "Poker Texas Hold'em: cada jogador recebe 2 cartas fechadas e a mesa abre até 5 cartas comunitárias.",
        "Ganha o pote quem formar a melhor mão de 5 cartas usando qualquer combinação das 7, "
        "ou quem continuar sozinho na mão depois que todos os outros desistirem.",
        "Uma mão tem quatro rodadas de apostas: pré-flop (só as suas cartas), flop (3 cartas na mesa), "
        "turn (4ª carta) e river (5ª carta). Depois do river acontece o showdown: as cartas são mostradas.",
        "Antes das cartas, os dois jogadores à esquerda do botão D pagam os blinds (apostas obrigatórias).",
    ]),
    ("Ranking das mãos", []),
    ("Apostas", [
        "Desistir (F): abandona a mão e o que você já apostou.",
        "Passar (C): continua sem apostar, quando ninguém apostou antes de você.",
        "Pagar (C): iguala a maior aposta da rodada.",
        "Apostar / Aumentar (R): coloca mais fichas. Use o controle deslizante, a rodinha do mouse, "
        "as setas ou os atalhos ½ Pote, Pote e All-in.",
        "All-in: aposta todas as suas fichas. Se você não tiver o suficiente para pagar, "
        "disputa só a parte do pote que conseguiu cobrir (pote lateral).",
    ]),
    ("Power-ups", []),
    ("Mini games e modalidades", [
        "A cada 2 mãos, todos os jogadores da mesa disputam um mini game. "
        "Quem vencer escolhe a modalidade de poker das mãos seguintes, até o próximo mini game.",
        "Escalada: aperte ESPAÇO o mais rápido que puder. Ganha quem chegar primeiro ao topo do prédio.",
        "Corrida: alterne as setas ESQUERDA e DIREITA para correr e aperte CIMA para pular as barreiras. "
        "Bater numa barreira deixa você tonto por 1 segundo.",
        "Quiz: 3 perguntas de conhecimentos gerais, 10 segundos cada. Acerto vale 100 pontos mais um bônus "
        "de até 100 pela rapidez.",
        "Modalidades: Texas Hold'em (2 cartas), Omaha 4, 5 e 6 (a mão usa exatamente 2 cartas suas + 3 da mesa) "
        "e Pineapple (3 cartas; depois das apostas do pré-flop você descarta 1).",
    ]),
    ("Modos e controles", [
        "Cash Game: você leva fichas do seu saldo para a mesa e pode sair quando quiser. "
        "Low, Medium e High Stakes mudam o tamanho dos blinds.",
        "Torneio (Sit & Go): 6 jogadores com 1.500 fichas. Os blinds sobem a cada 8 mãos e quem perde tudo sai. "
        "1º lugar leva 65% do prêmio e 2º lugar 35%.",
        "Bots: Fácil (pagam demais), Médio (jogam direto) e Difícil (calculam as chances e blefam).",
        "Teclas: F desistir, C passar/pagar, R aumentar, setas mudam a aposta, 1-4 usam power-ups, "
        "Espaço próxima mão, Esc pausa, F11 tela cheia.",
    ]),
]
RANKING_PAGE = 1
POWERUPS_PAGE = 3


class TutorialScene(Scene):
    """Páginas de instruções navegáveis com as setas ou os botões."""

    def __init__(self, app, overlay=False):
        super().__init__(app)
        self.overlay = overlay
        self.page = 0
        self.backdrop = Backdrop(seed=5)
        cx = C.WIDTH // 2
        self.prev_btn = Button((cx - 330, 640, 200, 52), "< Anterior", lambda: self._go(-1), "secondary", 24, pygame.K_LEFT)
        self.next_btn = Button((cx + 130, 640, 200, 52), "Próxima >", lambda: self._go(1), "primary", 24, pygame.K_RIGHT)
        self.back_btn = Button((30, 24, 130, 44), "< Voltar", self._back, "ghost", 24, pygame.K_ESCAPE)
        self.buttons = [self.prev_btn, self.next_btn, self.back_btn]

    def _go(self, step):
        """Anda ``step`` páginas (sem passar da primeira nem da última)."""
        self.page = max(0, min(len(PAGES) - 1, self.page + step))

    def _back(self):
        """Volta para o menu, ou para a pausa se foi aberta por cima da mesa."""
        if self.overlay:
            self.app.pop()
        else:
            from .menu import MenuScene
            self.app.replace(MenuScene(self.app))

    def update(self, dt):
        """Anima o fundo e desliga as setas nas pontas."""
        self.backdrop.update(dt)
        self.prev_btn.enabled = self.page > 0
        self.next_btn.enabled = self.page < len(PAGES) - 1
        super().update(dt)

    def draw(self, surface):
        """Título, caixa com o conteúdo da página e o número da página."""
        self.backdrop.draw(surface)
        title, paragraphs = PAGES[self.page]
        cx = C.WIDTH // 2
        draw.text(surface, "Como jogar", (cx, 46), 30, C.TEXT_DIM, True, "center")
        draw.text(surface, title, (cx, 96), 52, C.ACCENT, True, "center")
        box = pygame.Rect(140, 140, C.WIDTH - 280, 480)
        draw.panel(surface, box, C.PANEL, C.PANEL_BORDER, 16)
        if self.page == RANKING_PAGE:
            self._draw_ranking(surface, box)
        elif self.page == POWERUPS_PAGE:
            self._draw_powerups(surface, box)
        else:
            y = box.top + 30
            for paragraph in paragraphs:
                pygame.draw.circle(surface, C.ACCENT, (box.left + 40, y + 11), 5)
                y += draw.text_block(surface, paragraph, pygame.Rect(box.left + 60, y, box.width - 100, 200), 26, C.TEXT, 6) + 18
        draw.text(surface, f"{self.page + 1} / {len(PAGES)}", (cx, 666), 24, C.TEXT_DIM, False, "center")
        super().draw(surface)

    def _draw_ranking(self, surface, box):
        """As 9 mãos em duas colunas, da melhor para a pior, com cartas de exemplo."""
        for i, (name, cards) in enumerate(HAND_EXAMPLES):
            col, row = i % 2, i // 2
            x = box.left + 40 + col * 500
            y = box.top + 26 + row * 90
            draw.text(surface, f"{i + 1}. {name}", (x, y + 24), 26, C.TEXT, True, "midleft")
            for k, (rank, suit) in enumerate(cards):
                draw.draw_card(surface, Card(rank, suit), (x + 222 + k * 46, y + 26), 42, 58)

    def _draw_powerups(self, surface, box):
        """Como a roleta funciona e a lista de power-ups com a chance de cada um."""
        intro = (f"A cada {SPIN_EVERY} mãos você gira a roleta e ganha um power-up (guarda até {MAX_INVENTORY}). "
                 "Antes de girar, pode pagar fichas para tirar power-ups da roleta: quanto maior a chance do power-up, "
                 "mais caro (um comum custa uns 21 big blinds) e cada remoção encarece as próximas em 50%. "
                 "Cada power-up é usado uma vez e vale para a mão atual.")
        h = draw.text_block(surface, intro, pygame.Rect(box.left + 30, box.top + 20, box.width - 60, 100), 23, C.TEXT_DIM, 4)
        total = sum(cls().weight for cls in ALL_POWERUPS)
        y = box.top + 30 + h
        for i, cls in enumerate(ALL_POWERUPS):
            p = cls()
            draw.powerup_icon(surface, p, (box.left + 50, y + 20), 18)
            draw.text(surface, p.name, (box.left + 80, y + 4), 24, p.color, True)
            draw.text(surface, f"{p.rarity[0]} • {p.weight / total:.0%}", (box.left + 80, y + 26), 19, C.TEXT_DIM)
            draw.text_block(surface, p.description, pygame.Rect(box.left + 300, y + 4, box.width - 330, 50), 21, C.TEXT, 2)
            y += 52
