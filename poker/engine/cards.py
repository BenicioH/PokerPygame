"""Cartas e baralho.

Uma carta é representada por um valor (2 a 14, onde 11 = J, 12 = Q, 13 = K e
14 = A) e um naipe (0 a 3). O baralho é uma lista embaralhada de 52 cartas,
e a próxima carta a sair é sempre a do fim da lista (``pop`` é O(1)).
"""

import random

RANK_NAMES = {11: "J", 12: "Q", 13: "K", 14: "A"}
SUIT_NAMES = ["espadas", "copas", "ouros", "paus"]
SUIT_SYMBOLS = ["♠", "♥", "♦", "♣"]

RED_SUITS = (1, 2)


class Card:
    """Uma carta do baralho.

    Atributos:
        rank: valor da carta, de 2 a 14 (ás vale 14).
        suit: naipe, de 0 a 3 (índice em ``SUIT_NAMES``).
    """

    __slots__ = ("rank", "suit")

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    @property
    def rank_label(self):
        """Texto do valor, por exemplo ``"A"``, ``"10"`` ou ``"7"``."""
        return RANK_NAMES.get(self.rank, str(self.rank))

    @property
    def is_red(self):
        """Verdadeiro para copas e ouros."""
        return self.suit in RED_SUITS

    def __eq__(self, other):
        return isinstance(other, Card) and self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return self.rank * 4 + self.suit

    def __str__(self):
        """Nome legível, por exemplo ``"K de copas"`` (usado nas mensagens)."""
        return f"{self.rank_label} de {SUIT_NAMES[self.suit]}"

    def __repr__(self):
        return f"{self.rank_label}{SUIT_SYMBOLS[self.suit]}"


def full_deck():
    """Devolve uma lista nova com as 52 cartas, em ordem."""
    return [Card(rank, suit) for suit in range(4) for rank in range(2, 15)]


class Deck:
    """Baralho embaralhado de onde as cartas da mão são tiradas.

    O baralho permite "espiar" a próxima carta (power-up Próxima Carta) e
    travar essa carta para que nenhum outro efeito a troque depois que o
    jogador já a viu.
    """

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.cards = full_deck()
        self.rng.shuffle(self.cards)
        self.locked = 0

    def draw(self):
        """Tira a carta do topo."""
        if self.locked > 0:
            self.locked -= 1
        return self.cards.pop()

    def draw_unlocked(self):
        """Tira a primeira carta que ainda não foi espiada.

        Usado pela troca de carta (Mulligan) para não roubar a carta que o
        jogador já viu com o power-up Próxima Carta.
        """
        return self.cards.pop(-1 - self.locked)

    def peek(self):
        """Mostra a carta do topo sem tirá-la e a trava no lugar."""
        self.locked = max(self.locked, 1)
        return self.cards[-1]

    def put_back(self, card):
        """Devolve uma carta em uma posição aleatória abaixo das cartas travadas."""
        below_locked = len(self.cards) - self.locked
        self.cards.insert(self.rng.randint(0, below_locked), card)
