"""Modalidades de poker: Texas Hold'em, Omaha (4, 5 e 6 cartas) e Pineapple.

Todas usam a mesma mesa, as mesmas apostas e as mesmas 5 cartas
comunitárias. O que muda é:

* quantas cartas fechadas cada jogador recebe;
* como a melhor mão é montada:
    - Hold'em e Pineapple: as melhores 5 entre as suas cartas e as da mesa;
    - Omaha: OBRIGATORIAMENTE 2 cartas suas + 3 da mesa;
* no Pineapple, cada jogador recebe 3 cartas e descarta 1 antes do flop.
"""

from itertools import combinations

from .evaluator import evaluate, hand_name


class Variant:
    """Uma modalidade de poker.

    Atributos:
        key: identificador (``"holdem"``, ``"omaha4"``...).
        name: nome exibido.
        hole_cards: cartas fechadas distribuídas para cada jogador.
        discard: se cada jogador descarta 1 carta antes do flop (Pineapple).
        description: explicação curta para a escolha da modalidade.
        cost: quanto avaliar uma mão custa, comparado ao Hold'em (usado para
            reduzir as simulações dos bots e do Oráculo nas modalidades pesadas).
    """

    def __init__(self, key, name, hole_cards, description, discard=False):
        self.key = key
        self.name = name
        self.hole_cards = hole_cards
        self.description = description
        self.discard = discard
        self.cost = 1

    def best(self, hole, board):
        """Pontuação comparável da melhor mão (igual a :func:`evaluate`)."""
        return evaluate(list(hole) + list(board))

    def best_cards(self, hole, board):
        """As cartas que formam a melhor mão (usado para destacá-las na mesa)."""
        cards = list(hole) + list(board)
        if len(cards) <= 5:
            return tuple(cards)
        return max(combinations(cards, 5), key=lambda combo: evaluate(list(combo)))

    def hand_name(self, hole, board):
        """Nome da melhor mão, por exemplo "Dois pares"."""
        return hand_name(self.best(hole, board))


class OmahaVariant(Variant):
    """Omaha: a mão é sempre 2 cartas fechadas + 3 cartas da mesa."""

    def __init__(self, key, name, hole_cards, description):
        super().__init__(key, name, hole_cards, description)
        pairs = hole_cards * (hole_cards - 1) // 2
        self.cost = max(1, pairs * 10 // 3)

    def _options(self, hole, board):
        take = min(3, len(board))
        for mine in combinations(hole, 2):
            for shared in combinations(board, take):
                yield list(mine) + list(shared)

    def best(self, hole, board):
        return max(evaluate(cards) for cards in self._options(hole, board))

    def best_cards(self, hole, board):
        return tuple(max(self._options(hole, board), key=evaluate))


HOLDEM = Variant("holdem", "Texas Hold'em", 2, "2 cartas. A melhor mão usa quaisquer 5 das 7 cartas.")
VARIANTS = {
    "holdem": HOLDEM,
    "omaha4": OmahaVariant("omaha4", "Omaha 4", 4, "4 cartas. A mão usa exatamente 2 suas + 3 da mesa."),
    "omaha5": OmahaVariant("omaha5", "Omaha 5", 5, "5 cartas. A mão usa exatamente 2 suas + 3 da mesa."),
    "omaha6": OmahaVariant("omaha6", "Omaha 6", 6, "6 cartas. A mão usa exatamente 2 suas + 3 da mesa."),
    "pineapple": Variant("pineapple", "Pineapple", 3,
                         "3 cartas. Depois das apostas do pré-flop, cada um descarta 1. O resto é Hold'em.",
                         discard=True),
}


def get(key):
    """Modalidade a partir da chave (Hold'em se a chave for desconhecida)."""
    return VARIANTS.get(key, HOLDEM)


def preflop_value(cards):
    """Nota rápida de duas cartas, usada pelos bots para escolher o descarte.

    Pares valem muito; cartas altas, do mesmo naipe e próximas valem um pouco mais.
    """
    a, b = cards
    high, low = max(a.rank, b.rank), min(a.rank, b.rank)
    score = high + low / 2
    if a.rank == b.rank:
        score += 20 + a.rank
    if a.suit == b.suit:
        score += 4
    gap = high - low
    if 0 < gap <= 2:
        score += 3 - gap
    return score


def best_discard(hole):
    """Índice da carta que um bot descarta no Pineapple (fica com o melhor par de cartas)."""
    def value_without(index):
        return preflop_value([card for k, card in enumerate(hole) if k != index])

    return max(range(len(hole)), key=value_without)
