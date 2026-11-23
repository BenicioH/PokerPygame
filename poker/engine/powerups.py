"""Power-ups e a roleta que os sorteia.

A cada 3 mãos o jogador gira uma roleta e ganha um power-up. Cada power-up
tem uma raridade: quanto mais forte, menor a fatia na roleta. Antes de girar
o jogador pode pagar fichas para tirar power-ups da roleta, o que aumenta a
chance dos outros.

Cada power-up é usado uma única vez e vale para a mão em que foi usado.
Novos power-ups são criados como subclasses de :class:`PowerUp` e
registrados em :data:`ALL_POWERUPS`.
"""

import random

from .equity import equity_known, find_outs

COMMON = ("Comum", 30, (120, 200, 255))
UNCOMMON = ("Incomum", 16, (110, 230, 140))
RARE = ("Raro", 8, (200, 130, 255))
LEGENDARY = ("Lendário", 3, (255, 190, 60))

SPIN_EVERY = 3
MAX_INVENTORY = 4
REMOVE_BASE_BB = 5
REMOVE_PER_PERCENT_BB = 0.6
REMOVE_GROWTH = 1.5


class UseResult:
    """O que a interface deve mostrar depois que um power-up é usado.

    Atributos:
        ok: se o power-up foi realmente usado.
        message: texto para o jogador.
        data: informações extras para desenhar (cartas, porcentagens...).
    """

    def __init__(self, ok, message, **data):
        self.ok = ok
        self.message = message
        self.data = data


class PowerUp:
    """Base de todos os power-ups.

    Atributos de classe:
        key: identificador único (usado para salvar e para os ícones).
        name / description: textos da interface.
        rarity: uma das tuplas de raridade acima.
        symbol: letra ou sinal curto desenhado no ícone.
        target: ``None`` se não precisa de alvo, ``"own_card"`` se o jogador
            escolhe uma das suas cartas, ``"opponent"`` se escolhe um adversário.
    """

    key = "base"
    name = "Power-up"
    description = ""
    rarity = COMMON
    symbol = "?"
    target = None

    @property
    def weight(self):
        """Peso na roleta (fatia proporcional)."""
        return self.rarity[1]

    @property
    def color(self):
        """Cor da raridade."""
        return self.rarity[2]

    def can_use(self, hand, player):
        """Verifica se pode ser usado agora.

        Retorna:
            ``(True, "")`` ou ``(False, motivo)``.
        """
        if hand is None or hand.finished or not player.in_hand:
            return False, "Só durante uma mão em que você está jogando."
        reason = self.blocked_reason(hand)
        if reason:
            return False, reason
        return True, ""

    def blocked_reason(self, hand):
        """Regra extra de cada power-up: o motivo para não usar agora, ou ``""``."""
        return ""

    def use(self, hand, player, target=None):
        """Aplica o efeito. As subclasses devem sobrescrever."""
        raise NotImplementedError


class LuckyClover(PowerUp):
    """Trevo da Sorte: as próximas cartas da mesa tendem a ajudar você."""

    key = "luck"
    name = "Trevo da Sorte"
    description = "+20% de sorte: cada carta da mesa tem 20% de chance de ser a melhor entre 4 para você."
    rarity = COMMON
    symbol = "+%"

    def blocked_reason(self, hand):
        return "Não há mais cartas para abrir." if len(hand.board) == 5 else ""

    def use(self, hand, player, target=None):
        hand.lucky_seats.add(hand.index_of(player))
        return UseResult(True, "A sorte está do seu lado nesta mão!")


class NextCard(PowerUp):
    """Próxima Carta: mostra a próxima carta da mesa (não funciona no river)."""

    key = "peek"
    name = "Próxima Carta"
    description = "Mostra a próxima carta que vai abrir na mesa. Não funciona no river."
    rarity = COMMON
    symbol = ">"

    def blocked_reason(self, hand):
        return "Não funciona no river." if hand.street in ("river", "showdown") else ""

    def use(self, hand, player, target=None):
        card = hand.deck.peek()
        return UseResult(True, f"A próxima carta será {card}.", card=card)


class Mulligan(PowerUp):
    """Troca: troca uma das suas cartas por outra do baralho."""

    key = "swap"
    name = "Troca"
    description = "Troque uma das suas cartas por uma nova. Clique na carta depois de ativar. Até o turn."
    rarity = UNCOMMON
    symbol = "<>"
    target = "own_card"

    def blocked_reason(self, hand):
        if hand.street in ("river", "showdown"):
            return "Só até o turn."
        if hand.awaiting_discard:
            return "Espere o descarte do Pineapple."
        return ""

    def use(self, hand, player, target=None):
        events = hand.swap_hole_card(player, target or 0)
        old, new = events[0].cards
        return UseResult(True, f"Você trocou {old} por {new}.", events=events)


class OutsVision(PowerUp):
    """Raio-X de Outs: lista as cartas que melhoram a sua mão."""

    key = "outs"
    name = "Raio-X de Outs"
    description = "Mostra todas as cartas que melhoram a sua mão e a chance de vir uma delas. Flop ou turn."
    rarity = UNCOMMON
    symbol = "X"

    def blocked_reason(self, hand):
        return "Só no flop ou no turn." if len(hand.board) not in (3, 4) else ""

    def use(self, hand, player, target=None):
        outs = find_outs(player.hole, hand.board, hand.variant)
        unseen = 52 - len(player.hole) - len(hand.board)
        if len(hand.board) == 3:
            chance = 1 - ((unseen - len(outs)) / unseen) * ((unseen - 1 - len(outs)) / (unseen - 1))
        else:
            chance = len(outs) / unseen
        return UseResult(True, f"{len(outs)} outs ({chance:.0%} de chance de melhorar).",
                         outs=outs, chance=chance)


class MindRead(PowerUp):
    """Leitura: revela uma carta de um adversário escolhido."""

    key = "read"
    name = "Leitura"
    description = "Revela uma das cartas de um adversário. Clique no adversário depois de ativar."
    rarity = RARE
    symbol = "@"
    target = "opponent"

    def use(self, hand, player, target=None):
        if target is None or not target.in_hand or target is player:
            return UseResult(False, "Escolha um adversário que ainda está na mão.")
        hidden = [i for i in range(len(target.hole)) if i not in target.revealed]
        if not hidden:
            return UseResult(False, "Você já conhece uma carta desse jogador.")
        index = random.choice(hidden)
        target.revealed.add(index)
        return UseResult(True, f"{target.name} tem {target.hole[index]}.", card=target.hole[index], index=index)


class Shield(PowerUp):
    """Escudo: se perder no showdown, recebe metade do que apostou."""

    key = "shield"
    name = "Escudo"
    description = "Se você perder no showdown desta mão, recebe de volta metade do que apostou."
    rarity = RARE
    symbol = "U"

    def use(self, hand, player, target=None):
        hand.shield_seats.add(hand.index_of(player))
        return UseResult(True, "Escudo ativo: perder no showdown devolve metade da sua aposta.")


class TrueOdds(PowerUp):
    """Oráculo: a sua chance real de ganhar contra a de cada adversário."""

    key = "odds"
    name = "Oráculo"
    description = "Mostra a sua chance real de ganhar e a de cada adversário, sem mostrar as cartas deles."
    rarity = LEGENDARY
    symbol = "%"

    def use(self, hand, player, target=None):
        alive = [p for p in hand.players if p.in_hand]
        equities = equity_known([p.hole for p in alive], hand.board, iterations=3000, variant=hand.variant)
        table = {p.seat: e for p, e in zip(alive, equities)}
        mine = table[player.seat]
        return UseResult(True, f"Sua chance de ganhar: {mine:.0%}.", equities=table)


ALL_POWERUPS = [LuckyClover, NextCard, Mulligan, OutsVision, MindRead, Shield, TrueOdds]
BY_KEY = {cls.key: cls for cls in ALL_POWERUPS}


def create(key):
    """Cria um power-up a partir da sua chave (usado ao carregar o jogo salvo)."""
    return BY_KEY[key]()


class Roulette:
    """A roleta de power-ups de um giro.

    Args:
        big_blind: usado para calcular o custo de remover power-ups.
        rng: gerador aleatório.
    """

    def __init__(self, big_blind, rng=None):
        self.rng = rng or random.Random()
        self.big_blind = big_blind
        self.entries = [cls() for cls in ALL_POWERUPS]
        self.removed = set()

    @property
    def active(self):
        """Power-ups que ainda estão na roleta."""
        return [p for p in self.entries if p.key not in self.removed]

    def probabilities(self):
        """Chance de cada power-up ativo, em um dicionário ``chave -> fração``."""
        total = sum(p.weight for p in self.active)
        return {p.key: p.weight / total for p in self.active}

    def removal_cost(self, key):
        """Preço para tirar ``key`` da roleta agora.

        Cresce com a chance atual do power-up (tirar um comum é caro) e fica
        50% mais caro a cada remoção já feita neste giro.
        """
        chance = self.probabilities().get(key, 0.0) * 100
        bbs = (REMOVE_BASE_BB + REMOVE_PER_PERCENT_BB * chance) * (REMOVE_GROWTH ** len(self.removed))
        return int(round(bbs * self.big_blind))

    def removal_costs(self):
        """Preço de remoção de cada power-up ainda na roleta."""
        return {p.key: self.removal_cost(p.key) for p in self.active}

    def can_remove(self, key, chips):
        """Se ``key`` pode ser removido pagando com ``chips`` fichas."""
        return key not in self.removed and len(self.active) > 1 and chips >= self.removal_cost(key)

    def remove(self, key):
        """Tira ``key`` da roleta e devolve quanto custou."""
        cost = self.removal_cost(key)
        self.removed.add(key)
        return cost

    def spin(self):
        """Sorteia um power-up respeitando os pesos."""
        active = self.active
        return self.rng.choices(active, weights=[p.weight for p in active], k=1)[0]
