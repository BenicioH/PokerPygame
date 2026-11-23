"""Estratégias dos bots.

Todos os bots seguem a mesma ideia: estimar a força da mão (a chance de
ganhar contra mãos aleatórias, via :func:`equity_vs_random`) e comparar com o
preço para continuar (pot odds). O que muda entre as dificuldades é:

* **Fácil**: estimativa grosseira e cheia de ruído, paga demais, quase não
  aumenta e nunca blefa.
* **Médio**: estimativa razoável, aposta mãos boas e desiste das ruins.
* **Difícil**: estimativa precisa, considera a posição, faz semi-blefes,
  varia o tamanho das apostas e às vezes faz slow-play com mãos fortes.
"""

import random

from .equity import equity_vs_random


class BotStrategy:
    """Classe base. As subclasses ajustam os parâmetros de comportamento.

    Atributos de classe:
        label: nome da dificuldade mostrado na interface.
        samples: simulações de Monte Carlo por decisão (mais = mais preciso).
        noise: erro aleatório somado à força estimada da mão.
        aggression: quanto acima das pot odds o bot precisa estar para aumentar.
        bluff: chance de apostar/aumentar com uma mão fraca.
        call_bias: tendência a pagar mesmo sem odds (positivo = paga mais).
        slowplay: chance de só pagar com uma mão muito forte.
        range_respect: quanto o bot desconta da sua força diante de apostas grandes.
        loose_call: chance de pagar uma aposta pequena (até 1 big blind) sem odds.
    """

    label = "Base"
    samples = 150
    noise = 0.0
    aggression = 0.15
    bluff = 0.0
    call_bias = 0.0
    slowplay = 0.0
    range_respect = 0.0
    loose_call = 0.3

    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def strength(self, hand, player):
        """Chance estimada de ganhar o pote (0 a 1), com o ruído da dificuldade."""
        opponents = max(1, hand.opponents_in_hand(player))
        equity = equity_vs_random(player.hole, hand.board, opponents, self.samples, self.rng, hand.variant)
        return max(0.0, min(1.0, equity + self.rng.uniform(-self.noise, self.noise)))

    def decide(self, hand, player):
        """Escolhe a ação do bot.

        Retorna:
            Tupla ``(tipo, valor)`` aceita por :meth:`Hand.act`.
        """
        legal = hand.legal()
        strength = self.strength(hand, player)
        pot = hand.pot
        to_call = legal.to_call
        price = to_call / (pot + to_call) if to_call else 0.0
        opponents = max(1, hand.opponents_in_hand(player))
        fair = 1.0 / (opponents + 1)

        facing_raise = hand.current_bet > (hand.bb if hand.street == "preflop" else 0)
        if facing_raise:
            strength -= self.range_respect * min(1.0, to_call / max(pot, 1))

        strong = strength > fair + self.aggression + 0.25
        good = strength > fair + self.aggression
        wants_bluff = self.rng.random() < self.bluff_chance(hand, player) and hand.street != "preflop"

        if legal.can_raise and (strong or (not facing_raise and (good or wants_bluff))):
            if strong and self.rng.random() < self.slowplay and to_call == 0:
                return ("check", 0)
            return ("raise", self._raise_size(hand, legal, strength, strong))

        if to_call == 0:
            return ("check", 0)

        if strength + self.call_bias >= price:
            return ("call", 0)
        if to_call <= hand.bb and self.rng.random() < self.loose_call + self.call_bias:
            return ("call", 0)
        return ("fold", 0)

    def bluff_chance(self, hand, player):
        """Chance de blefar nesta decisão (a base usa sempre ``bluff``)."""
        return self.bluff

    def _raise_size(self, hand, legal, strength, strong):
        """Valor total da aposta: uma fração do pote, maior para mãos fortes."""
        pot = hand.pot + legal.to_call
        if hand.street == "preflop":
            target = int(hand.current_bet * self.rng.choice((2.5, 3, 3)))
        else:
            fraction = self.rng.choice((0.5, 0.66, 0.75, 1.0)) if strong else self.rng.choice((0.33, 0.5, 0.66))
            target = hand.current_bet + int(pot * fraction)
        if strong and strength > 0.85 and self.rng.random() < 0.25:
            target = legal.max_raise_to
        return max(legal.min_raise_to, min(target, legal.max_raise_to))


class EasyBot(BotStrategy):
    """Bot fácil: paga muito, raramente aumenta, não blefa."""

    label = "Fácil"
    samples = 100
    noise = 0.13
    aggression = 0.27
    bluff = 0.0
    call_bias = 0.10
    range_respect = 0.08


class MediumBot(BotStrategy):
    """Bot médio: joga mãos boas de forma direta."""

    label = "Médio"
    samples = 200
    noise = 0.05
    aggression = 0.13
    bluff = 0.07
    call_bias = -0.01
    range_respect = 0.2


class HardBot(BotStrategy):
    """Bot difícil: preciso, posicional e capaz de blefar."""

    label = "Difícil"
    samples = 400
    noise = 0.01
    aggression = 0.09
    bluff = 0.13
    call_bias = -0.03
    slowplay = 0.2
    range_respect = 0.3
    loose_call = 0.12

    def bluff_chance(self, hand, player):
        """Blefa mais (25%) contra até 2 adversários que só passaram depois do flop."""
        if hand.street != "preflop" and hand.current_bet == 0 and hand.opponents_in_hand(player) <= 2:
            return 0.25
        return self.bluff


DIFFICULTIES = {"easy": EasyBot, "medium": MediumBot, "hard": HardBot}


def make_bot(difficulty, rng=None):
    """Cria a estratégia para ``"easy"``, ``"medium"`` ou ``"hard"``."""
    return DIFFICULTIES[difficulty](rng)
