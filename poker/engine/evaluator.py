"""Avaliação de mãos de poker (Texas Hold'em).

A função principal, :func:`evaluate`, recebe de 5 a 7 cartas e devolve uma
tupla que pode ser comparada diretamente: a maior tupla é a melhor mão.

O primeiro número da tupla é a categoria (0 = carta alta ... 8 = straight
flush) e os seguintes são os desempates, do mais importante para o menos
importante. Exemplo: dois pares de K e 7 com kicker 4 viram ``(2, 13, 7, 4)``.

A avaliação olha as 7 cartas de uma vez (contando valores e naipes) em vez
de testar as 21 combinações de 5 cartas, o que a deixa rápida o suficiente
para as simulações de Monte Carlo usadas pelos bots e pelos power-ups.
"""

HIGH_CARD = 0
PAIR = 1
TWO_PAIR = 2
TRIPS = 3
STRAIGHT = 4
FLUSH = 5
FULL_HOUSE = 6
QUADS = 7
STRAIGHT_FLUSH = 8

CATEGORY_NAMES = [
    "Carta alta",
    "Par",
    "Dois pares",
    "Trinca",
    "Sequência",
    "Flush",
    "Full house",
    "Quadra",
    "Straight flush",
]


def _straight_high(ranks):
    """Devolve a carta mais alta de uma sequência em ``ranks`` ou 0.

    ``ranks`` é um conjunto de valores. O ás também conta como 1 para a
    sequência A-2-3-4-5 (a "roda"), cuja carta mais alta é o 5.
    """
    for high in range(14, 5, -1):
        if all((high - i) in ranks for i in range(5)):
            return high
    if {14, 2, 3, 4, 5} <= ranks:
        return 5
    return 0


def evaluate(cards):
    """Avalia a melhor mão de 5 cartas dentro de ``cards`` (5 a 7 cartas).

    Retorna:
        Uma tupla comparável ``(categoria, desempate1, desempate2, ...)``.
    """
    counts = {}
    suits = {}
    for card in cards:
        counts[card.rank] = counts.get(card.rank, 0) + 1
        suits.setdefault(card.suit, []).append(card.rank)

    flush_ranks = next((ranks for ranks in suits.values() if len(ranks) >= 5), None)
    if flush_ranks is not None:
        high = _straight_high(set(flush_ranks))
        if high:
            return (STRAIGHT_FLUSH, high)

    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)

    if groups[0][1] == 4:
        quad = groups[0][0]
        kicker = max((rank for rank in counts if rank != quad), default=0)
        return (QUADS, quad, kicker)

    if groups[0][1] == 3 and len(groups) > 1 and groups[1][1] >= 2:
        return (FULL_HOUSE, groups[0][0], groups[1][0])

    if flush_ranks is not None:
        return (FLUSH,) + tuple(sorted(flush_ranks, reverse=True)[:5])

    high = _straight_high(set(counts))
    if high:
        return (STRAIGHT, high)

    singles = sorted((rank for rank, n in counts.items() if n == 1), reverse=True)

    if groups[0][1] == 3:
        return (TRIPS, groups[0][0]) + tuple(singles[:2])

    pairs = [rank for rank, n in groups if n == 2]
    if len(pairs) >= 2:
        rest = [rank for rank in counts if rank not in pairs[:2]]
        return (TWO_PAIR, pairs[0], pairs[1], max(rest, default=0))

    if len(pairs) == 1:
        return (PAIR, pairs[0]) + tuple(singles[:3])

    return (HIGH_CARD,) + tuple(singles[:5])


def hand_name(score):
    """Nome em português da categoria de uma pontuação de :func:`evaluate`."""
    return CATEGORY_NAMES[score[0]]
