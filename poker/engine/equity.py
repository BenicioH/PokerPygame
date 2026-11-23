"""Cálculo de chances (equidade) e de outs.

Equidade é a fração do pote que um jogador ganharia, em média, se todas as
cartas que faltam fossem abertas. Quando há poucas possibilidades (no flop
e no turn) todas são testadas uma a uma; no pré-flop, que tem milhões de
combinações, é usada uma simulação de Monte Carlo (sorteios aleatórios).
"""

import itertools
import math
import random

from .cards import full_deck
from .evaluator import evaluate, hand_name
from .variants import HOLDEM

EXACT_LIMIT = 4400


def _remaining(excluded):
    """Cartas do baralho que não estão em ``excluded``."""
    used = set(excluded)
    return [card for card in full_deck() if card not in used]


def _share_wins(hands, board, totals, variant):
    """Avalia uma mesa completa e soma em ``totals`` a parte de cada vencedor."""
    scores = [variant.best(hand, board) for hand in hands]
    best = max(scores)
    winners = [i for i, score in enumerate(scores) if score == best]
    for i in winners:
        totals[i] += 1.0 / len(winners)


def equity_known(hands, board, iterations=1500, rng=None, variant=HOLDEM):
    """Chance de vitória de cada mão quando todas as mãos são conhecidas.

    Args:
        hands: lista com as cartas fechadas de cada jogador.
        board: cartas comunitárias já abertas (0 a 5).
        iterations: número de sorteios quando for preciso usar Monte Carlo.

    Retorna:
        Lista de frações entre 0 e 1, uma por mão, que somam 1.
    """
    rng = rng or random.Random()
    iterations = max(250, iterations // variant.cost)
    missing = 5 - len(board)
    deck = _remaining([card for hand in hands for card in hand] + list(board))
    totals = [0.0] * len(hands)

    combos = math.comb(len(deck), missing)
    if combos * variant.cost <= EXACT_LIMIT:
        for extra in itertools.combinations(deck, missing):
            _share_wins(hands, list(board) + list(extra), totals, variant)
        runs = combos
    else:
        for _ in range(iterations):
            _share_wins(hands, list(board) + rng.sample(deck, missing), totals, variant)
        runs = iterations
    return [total / runs for total in totals]


def equity_vs_random(hole, board, opponents, iterations=300, rng=None, variant=HOLDEM):
    """Chance de vitória de ``hole`` contra ``opponents`` mãos desconhecidas.

    Usado pelos bots, que não podem ver as cartas dos adversários: as mãos
    dos adversários são sorteadas a cada iteração.
    """
    rng = rng or random.Random()
    iterations = max(25, iterations // variant.cost)
    deck = _remaining(list(hole) + list(board))
    missing = 5 - len(board)
    size = len(hole)
    need = missing + size * opponents
    wins = 0.0
    for _ in range(iterations):
        drawn = rng.sample(deck, need)
        full_board = list(board) + drawn[:missing]
        mine = variant.best(hole, full_board)
        ties = 0
        lost = False
        for k in range(opponents):
            start = missing + size * k
            other = variant.best(drawn[start:start + size], full_board)
            if other > mine:
                lost = True
                break
            if other == mine:
                ties += 1
        if not lost:
            wins += 1.0 / (ties + 1)
    return wins / iterations


def find_outs(hole, board, variant=HOLDEM):
    """Lista as cartas que melhoram a categoria da mão do jogador.

    Uma carta só conta como out se a melhora usa as cartas do jogador, ou
    seja, se a mesa sozinha (com a carta nova) não forma a mesma coisa.
    Por exemplo, um par na mesa que dá dois pares para todo mundo não conta.

    Retorna:
        Lista de tuplas ``(carta, nome_da_mão_nova)``.
    """
    current = variant.best(hole, board)[0]
    outs = []
    for card in _remaining(list(hole) + list(board)):
        mine = variant.best(hole, list(board) + [card])
        if mine[0] <= current:
            continue
        if not variant.key.startswith("omaha"):
            board_only = evaluate(list(board) + [card])
            if board_only[0] >= mine[0]:
                continue
        outs.append((card, hand_name(mine)))
    return outs
