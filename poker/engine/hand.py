"""Uma mão de poker No-Limit (em qualquer modalidade), do blind ao showdown.

A classe :class:`Hand` é uma máquina de estados que não sabe nada de tela
nem de som. Ela é controlada por três chamadas:

* :meth:`Hand.start` posta os blinds e distribui as cartas;
* :meth:`Hand.act` aplica a decisão do jogador da vez (``to_act``);
* :meth:`Hand.advance` é chamada quando ninguém mais precisa agir na rodada
  de apostas: abre a próxima carta da mesa ou faz o showdown.

Cada chamada devolve uma lista de :class:`Event`. A interface usa esses
eventos para animar e tocar sons.
"""

import random
from dataclasses import dataclass, field

from .cards import Deck
from .evaluator import hand_name
from .variants import HOLDEM

LUCK_CHANCE = 0.20
LUCK_CANDIDATES = 4

STREET_NAMES = {
    "preflop": "Pré-flop",
    "flop": "Flop",
    "turn": "Turn",
    "river": "River",
    "showdown": "Showdown",
}
NEXT_STREET = {"preflop": "flop", "flop": "turn", "turn": "river"}
CARDS_PER_STREET = {"flop": 3, "turn": 1, "river": 1}


@dataclass
class Event:
    """Algo que aconteceu na mão e que a interface pode mostrar.

    ``kind`` pode ser: ``blind``, ``deal``, ``action``, ``collect``,
    ``board``, ``lucky``, ``reveal``, ``showdown``, ``win``, ``shield``,
    ``swap``, ``discard_phase`` ou ``discard``.
    """

    kind: str
    seat: int = -1
    amount: int = 0
    cards: list = field(default_factory=list)
    text: str = ""
    action: str = ""


@dataclass
class Legal:
    """O que o jogador da vez pode fazer."""

    to_call: int
    can_check: bool
    can_raise: bool
    min_raise_to: int
    max_raise_to: int


class Hand:
    """Estado e regras de uma mão.

    Args:
        players: jogadores com fichas, na ordem dos assentos.
        button: índice (em ``players``) de quem está com o botão do dealer.
        small_blind / big_blind: valores dos blinds.
        rng: gerador aleatório (permite repetir uma mão nos testes).
    """

    def __init__(self, players, button, small_blind, big_blind, rng=None, variant=HOLDEM):
        self.players = players
        self.button = button
        self.sb = small_blind
        self.bb = big_blind
        self.rng = rng or random.Random()
        self.variant = variant
        self.awaiting_discard = None
        self.deck = Deck(self.rng)
        self.board = []
        self.street = "preflop"
        self.finished = False
        self.current_bet = 0
        self.min_raise = big_blind
        self.to_act = None
        self.lucky_seats = set()
        self.shield_seats = set()
        self.winners = []

    @property
    def pot(self):
        """Total de fichas na mão, incluindo as apostas ainda na frente dos jogadores."""
        return sum(p.committed for p in self.players)

    @property
    def collected_pot(self):
        """Fichas já recolhidas para o centro da mesa."""
        return sum(p.committed - p.bet for p in self.players)

    @property
    def current_player(self):
        """Jogador da vez ou ``None``."""
        return None if self.to_act is None else self.players[self.to_act]

    def index_of(self, player):
        """Posição de ``player`` na lista de jogadores da mão."""
        return self.players.index(player)

    def legal(self):
        """Ações permitidas para o jogador da vez."""
        p = self.players[self.to_act]
        to_call = min(self.current_bet - p.bet, p.stack)
        max_to = p.bet + p.stack
        others_can_act = any(q.can_act for q in self.players if q is not p)
        return Legal(
            to_call=to_call,
            can_check=to_call == 0,
            can_raise=others_can_act and max_to > self.current_bet,
            min_raise_to=min(self.current_bet + self.min_raise, max_to),
            max_raise_to=max_to,
        )

    def opponents_in_hand(self, player):
        """Quantos adversários de ``player`` ainda disputam o pote."""
        return sum(1 for q in self.players if q is not player and q.in_hand)

    def start(self):
        """Posta os blinds, distribui as cartas e define quem age primeiro."""
        events = []
        for p in self.players:
            p.reset_for_hand()
        n = len(self.players)
        sb_i = self.button if n == 2 else self._next(self.button)
        bb_i = self._next(sb_i)
        self._post_blind(sb_i, self.sb, "SB", events)
        self._post_blind(bb_i, self.bb, "BB", events)
        self.current_bet = self.bb

        deal_order = [self.players[(sb_i + k) % n] for k in range(n)]
        for _ in range(self.variant.hole_cards):
            for p in deal_order:
                p.hole.append(self.deck.draw())
        for p in deal_order:
            events.append(Event("deal", seat=p.seat, cards=list(p.hole)))

        self.to_act = self._find_actor(self._next(bb_i))
        if self.to_act is None:
            self._reveal_if_all_in(events)
        return events

    def _post_blind(self, i, amount, label, events):
        """O jogador ``i`` coloca o blind (ou tudo o que tem, se for menos)."""
        p = self.players[i]
        paid = p.put_chips(amount)
        p.last_action = label
        events.append(Event("blind", seat=p.seat, amount=paid, text=f"{p.name} posta {label} de {paid}"))

    def act(self, kind, amount=0):
        """Aplica a ação do jogador da vez.

        Args:
            kind: ``"fold"``, ``"check"``, ``"call"`` ou ``"raise"``.
            amount: para ``"raise"``, o valor TOTAL da aposta na rodada
                (por exemplo "aumentar para 300").
        """
        if self.to_act is None or self.finished:
            return []
        index = self.to_act
        p = self.players[index]
        legal = self.legal()
        events = []

        if kind == "check" and not legal.can_check:
            kind = "call"
        target = max(legal.min_raise_to, min(amount, legal.max_raise_to))
        if kind == "raise" and (not legal.can_raise or target <= self.current_bet):
            kind = "call" if legal.to_call > 0 else "check"

        if kind == "fold":
            p.folded = True
            p.last_action = "Fold"
            events.append(Event("action", seat=p.seat, action="fold", text=f"{p.name} desiste"))
        elif kind == "check":
            p.last_action = "Check"
            events.append(Event("action", seat=p.seat, action="check", text=f"{p.name} passa"))
        elif kind == "call":
            paid = p.put_chips(legal.to_call)
            p.last_action = "All-in" if p.all_in else "Call"
            events.append(Event("action", seat=p.seat, action="call", amount=paid,
                                text=f"{p.name} paga {paid}" + (" (all-in)" if p.all_in else "")))
        else:
            self._raise_to(p, target, events)
        p.has_acted = True

        if sum(1 for q in self.players if q.in_hand) == 1:
            self._award_uncontested(events)
        else:
            self.to_act = self._find_actor(self._next(index))
            if self.to_act is None:
                self._reveal_if_all_in(events)
        return events

    def _raise_to(self, p, target, events):
        """Aposta (se ninguém apostou) ou aumenta até ``target`` fichas na rodada."""
        was_open = self.current_bet == 0
        p.put_chips(target - p.bet)
        raise_size = p.bet - self.current_bet
        if raise_size >= self.min_raise:
            self.min_raise = raise_size
            for q in self.players:
                if q is not p:
                    q.has_acted = False
        self.current_bet = p.bet
        word = "aposta" if was_open else "aumenta para"
        p.last_action = "All-in" if p.all_in else ("Bet" if was_open else "Raise")
        events.append(Event("action", seat=p.seat, action="raise", amount=p.bet,
                            text=f"{p.name} {word} {p.bet}" + (" (all-in)" if p.all_in else "")))

    def advance(self):
        """Fecha a rodada de apostas e abre a próxima carta (ou faz o showdown).

        Só faz algo quando ninguém precisa agir (``to_act is None``). Se os
        jogadores restantes estiverem all-in, cada chamada abre uma rua, o
        que deixa a interface mostrar as cartas uma de cada vez.
        """
        if self.finished or self.to_act is not None:
            return []

        if self.variant.discard and self.street == "preflop":
            if self.awaiting_discard is None:
                self.awaiting_discard = [p for p in self.players if p.in_hand and len(p.hole) > 2]
                if self.awaiting_discard:
                    return [Event("discard_phase")]
            if self.awaiting_discard:
                return []

        events = []
        if any(p.bet for p in self.players):
            events.append(Event("collect", amount=self.pot))
        for p in self.players:
            p.bet = 0
            p.has_acted = False
        self.current_bet = 0
        self.min_raise = self.bb

        if self.street == "river":
            self._showdown(events)
            return events

        self.street = NEXT_STREET[self.street]
        new_cards = [self._deal_board_card(events) for _ in range(CARDS_PER_STREET[self.street])]
        self.board.extend(new_cards)
        events.append(Event("board", cards=new_cards,
                            text=f"{STREET_NAMES[self.street]}: {', '.join(map(str, new_cards))}"))

        if sum(1 for p in self.players if p.can_act) >= 2:
            self.to_act = self._find_actor(self._next(self.button))
        return events

    def discard(self, player, card_index):
        """Pineapple: ``player`` joga fora a carta ``card_index``."""
        if not self.awaiting_discard or player not in self.awaiting_discard:
            return []
        card_index = max(0, min(card_index, len(player.hole) - 1))
        player.hole.pop(card_index)
        self.awaiting_discard.remove(player)
        return [Event("discard", seat=player.seat, text=f"{player.name} descartou uma carta")]

    def swap_hole_card(self, player, card_index):
        """Troca uma carta fechada de ``player`` por uma nova do baralho."""
        old = player.hole[card_index]
        new = self.deck.draw_unlocked()
        player.hole[card_index] = new
        return [Event("swap", seat=player.seat, cards=[old, new],
                      text=f"{player.name} trocou uma carta")]

    def _deal_board_card(self, events):
        """Tira a próxima carta da mesa, aplicando o Trevo da Sorte se ativo."""
        lucky = [self.players[i] for i in self.lucky_seats if self.players[i].in_hand]
        if lucky and self.deck.locked == 0 and self.rng.random() < LUCK_CHANCE:
            p = lucky[0]
            candidates = [self.deck.draw() for _ in range(LUCK_CANDIDATES)]
            best = max(candidates, key=lambda c: self.variant.best(p.hole, self.board + [c]))
            for card in candidates:
                if card is not best:
                    self.deck.put_back(card)
            events.append(Event("lucky", seat=p.seat, cards=[best], text="O trevo da sorte escolheu uma carta!"))
            return best
        return self.deck.draw()

    def _award_uncontested(self, events):
        """Todos desistiram menos um: ele leva o pote sem mostrar as cartas."""
        winner = next(p for p in self.players if p.in_hand)
        pot = self.pot
        events.append(Event("collect", amount=pot))
        for p in self.players:
            p.bet = 0
        winner.stack += pot
        self.winners = [(winner, pot, "")]
        events.append(Event("win", seat=winner.seat, amount=pot, text=f"{winner.name} ganha {pot}"))
        self._finish()

    def _reveal_if_all_in(self, events):
        """Se no máximo um jogador ainda pode apostar (os outros estão all-in), as cartas abrem."""
        contenders = [p for p in self.players if p.in_hand]
        still_betting = sum(1 for p in contenders if p.can_act)
        if len(contenders) >= 2 and still_betting <= 1 and not all(p.show_cards for p in contenders):
            for p in contenders:
                p.show_cards = True
            events.append(Event("reveal"))

    def build_pots(self):
        """Divide as fichas em pote principal e potes laterais.

        Cada nível de all-in de um jogador que não desistiu fecha um pote.
        Um jogador só pode ganhar os potes para os quais contribuiu até o
        fim. Fichas de quem desistiu acima do último nível vão para o último pote.

        Retorna:
            Lista de ``(valor, [jogadores_elegiveis])``, do principal ao último lateral.
        """
        alive = [p for p in self.players if p.in_hand]
        pots = []
        previous = 0
        for level in sorted({p.committed for p in alive}):
            amount = sum(min(p.committed, level) - min(p.committed, previous) for p in self.players)
            if amount > 0:
                pots.append((amount, [p for p in alive if p.committed >= level]))
            previous = level
        leftover = self.pot - sum(amount for amount, _ in pots)
        if leftover and pots:
            amount, eligible = pots[-1]
            pots[-1] = (amount + leftover, eligible)
        return pots

    def _showdown(self, events):
        """Compara as mãos, paga os potes e aplica o Escudo."""
        self.street = "showdown"
        alive = [p for p in self.players if p.in_hand]
        for p in alive:
            p.show_cards = True
        scores = {p: self.variant.best(p.hole, self.board) for p in alive}
        events.append(Event("showdown"))

        winnings = {p: 0 for p in self.players}
        pot_winners = set()
        for amount, eligible in self.build_pots():
            best = max(scores[p] for p in eligible)
            winners = self._by_position([p for p in eligible if scores[p] == best])
            share, rest = divmod(amount, len(winners))
            for w in winners:
                winnings[w] += share
            winnings[winners[0]] += rest
            pot_winners.update(winners)

        self._apply_shields(winnings, events)

        self.winners = []
        for p in self.players:
            won = winnings[p]
            if won <= 0:
                continue
            p.stack += won
            if p not in pot_winners:
                continue
            name = hand_name(scores[p])
            self.winners.append((p, won, name))
            events.append(Event("win", seat=p.seat, amount=won, text=f"{p.name} ganha {won} com {name}"))
        self._finish()

    def _apply_shields(self, winnings, events):
        """Escudo: quem perdeu o showdown recebe metade do que colocou de volta.

        O reembolso sai dos ganhos de quem venceu, começando por quem ganhou mais.
        """
        for i in sorted(self.shield_seats):
            p = self.players[i]
            if not p.in_hand or winnings[p] > 0:
                continue
            refund = p.committed // 2
            for w in sorted(self.players, key=lambda q: -winnings[q]):
                take = min(refund, winnings[w])
                winnings[w] -= take
                winnings[p] += take
                refund -= take
                if refund == 0:
                    break
            events.append(Event("shield", seat=p.seat, amount=winnings[p],
                                text=f"Escudo devolve {winnings[p]} para {p.name}"))

    def _finish(self):
        """Marca a mão como encerrada."""
        self.finished = True
        self.to_act = None

    def _next(self, i):
        """Índice do jogador seguinte (em volta da mesa)."""
        return (i + 1) % len(self.players)

    def _find_actor(self, start):
        """Primeiro jogador a partir de ``start`` que ainda precisa agir."""
        n = len(self.players)
        for k in range(n):
            i = (start + k) % n
            p = self.players[i]
            if p.can_act and (not p.has_acted or p.bet < self.current_bet):
                return i
        return None

    def _by_position(self, players):
        """Ordena jogadores a partir do primeiro à esquerda do botão."""
        n = len(self.players)
        return sorted(players, key=lambda p: (self.index_of(p) - self.button - 1) % n)
