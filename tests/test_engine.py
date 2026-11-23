"""Testes das regras do jogo (não precisam de janela nem de pygame).

Rodar com: python -m unittest discover tests
"""

import random
import unittest

from poker.engine.bots import make_bot
from poker.engine.cards import Card, Deck
from poker.engine.equity import equity_known, find_outs
from poker.engine.evaluator import (FLUSH, FULL_HOUSE, HIGH_CARD, PAIR, QUADS, STRAIGHT,
                                    STRAIGHT_FLUSH, TRIPS, TWO_PAIR, evaluate)
from poker.engine.hand import Hand
from poker.engine.player import Player
from poker.engine.powerups import NextCard, Roulette
from poker.engine.session import CashSession, TournamentSession

S, H, D, C = range(4)


def cards(*pairs):
    """Atalho: cards((14, S), (13, H)) -> [A♠, K♥]."""
    return [Card(rank, suit) for rank, suit in pairs]


class EvaluatorTest(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(evaluate(cards((10, H), (11, H), (12, H), (13, H), (14, H), (2, S), (3, D)))[0], STRAIGHT_FLUSH)
        self.assertEqual(evaluate(cards((8, S), (8, H), (8, D), (8, C), (2, S), (3, D), (4, C)))[0], QUADS)
        self.assertEqual(evaluate(cards((8, S), (8, H), (8, D), (5, C), (5, S), (3, D), (4, C)))[0], FULL_HOUSE)
        self.assertEqual(evaluate(cards((2, D), (6, D), (9, D), (11, D), (14, D), (3, S), (4, C)))[0], FLUSH)
        self.assertEqual(evaluate(cards((5, S), (6, H), (7, D), (8, C), (9, S), (13, D), (2, C)))[0], STRAIGHT)
        self.assertEqual(evaluate(cards((7, S), (7, H), (7, D), (12, C), (3, S), (9, D), (2, C)))[0], TRIPS)
        self.assertEqual(evaluate(cards((11, S), (11, H), (4, D), (4, C), (14, S), (9, D), (2, C)))[0], TWO_PAIR)
        self.assertEqual(evaluate(cards((10, S), (10, H), (2, D), (7, C), (13, S), (9, D), (3, C)))[0], PAIR)
        self.assertEqual(evaluate(cards((14, S), (9, H), (6, D), (4, C), (2, S), (11, D), (3, C)))[0], HIGH_CARD)

    def test_wheel_straight_is_five_high(self):
        wheel = evaluate(cards((14, S), (2, H), (3, D), (4, C), (5, S), (9, D), (13, C)))
        six_high = evaluate(cards((6, S), (2, H), (3, D), (4, C), (5, S), (9, D), (13, C)))
        self.assertEqual(wheel, (STRAIGHT, 5))
        self.assertGreater(six_high, wheel)

    def test_kickers_break_ties(self):
        board = cards((13, S), (13, H), (7, D), (4, C), (2, S))
        ace = evaluate(board + cards((14, D), (3, C)))
        queen = evaluate(board + cards((12, D), (3, C)))
        self.assertGreater(ace, queen)

    def test_two_trips_is_full_house(self):
        score = evaluate(cards((9, S), (9, H), (9, D), (5, C), (5, S), (5, D), (2, C)))
        self.assertEqual(score, (FULL_HOUSE, 9, 5))

    def test_partial_hands_do_not_crash(self):
        self.assertEqual(evaluate(cards((9, S), (9, H), (5, D), (5, C)))[0], TWO_PAIR)


class EquityTest(unittest.TestCase):
    def test_aces_beat_kings_about_80_percent(self):
        aa = cards((14, S), (14, H))
        kk = cards((13, S), (13, H))
        eq = equity_known([aa, kk], [], iterations=3000, rng=random.Random(1))
        self.assertAlmostEqual(sum(eq), 1.0, places=6)
        self.assertGreater(eq[0], 0.75)
        self.assertLess(eq[0], 0.88)

    def test_flush_draw_has_nine_outs(self):
        hole = cards((14, H), (9, H))
        board = cards((2, H), (7, H), (12, S))
        outs = [card for card, _ in find_outs(hole, board)]
        hearts = [card for card in outs if card.suit == H]
        self.assertEqual(len(hearts), 9)


class HandTest(unittest.TestCase):
    def make_players(self, stacks):
        players = []
        for i, stack in enumerate(stacks):
            p = Player(f"P{i}", stack)
            p.seat = i
            players.append(p)
        return players

    def test_blinds_and_first_to_act(self):
        players = self.make_players([100, 100, 100, 100])
        hand = Hand(players, 0, 1, 2, random.Random(1))
        hand.start()
        self.assertEqual(players[1].bet, 1)
        self.assertEqual(players[2].bet, 2)
        self.assertIs(hand.current_player, players[3])

    def test_heads_up_button_posts_small_blind(self):
        players = self.make_players([100, 100])
        hand = Hand(players, 0, 1, 2, random.Random(1))
        hand.start()
        self.assertEqual(players[0].bet, 1)
        self.assertIs(hand.current_player, players[0])

    def test_everyone_folds_to_big_blind(self):
        players = self.make_players([100, 100, 100])
        hand = Hand(players, 0, 1, 2, random.Random(1))
        hand.start()
        hand.act("fold")
        hand.act("fold")
        self.assertTrue(hand.finished)
        self.assertEqual(players[2].stack, 101)

    def test_side_pot(self):
        players = self.make_players([20, 100, 100])
        hand = Hand(players, 2, 1, 2, random.Random(3))
        hand.start()
        hand.act("raise", 20)
        hand.act("call")
        hand.act("raise", 60)
        hand.act("call")
        pots = hand.build_pots()
        self.assertEqual(pots[0][0], 60)
        self.assertEqual(len(pots[0][1]), 3)
        self.assertEqual(pots[1][0], 80)
        self.assertNotIn(players[0], pots[1][1])

    def test_chips_are_conserved_over_many_hands(self):
        rng = random.Random(7)
        session = CashSession("Eu", 200, "medium", "low", rng)
        session.human.bot = make_bot("medium", rng)
        for _ in range(60):
            if session.human.stack <= 0:
                session.rebuy(200)
            session.new_hand()
            hand = session.hand
            total = sum(p.stack for p in session.players) + hand.pot
            steps = 0
            while not hand.finished:
                steps += 1
                self.assertLess(steps, 400)
                if hand.to_act is None:
                    hand.advance()
                else:
                    p = hand.current_player
                    hand.act(*p.bot.decide(hand, p))
            self.assertEqual(sum(p.stack for p in session.players), total)
            session.end_hand()


class PowerUpTest(unittest.TestCase):
    def test_roulette_removal_cost(self):
        roulette = Roulette(10, random.Random(1))
        common, legendary = roulette.removal_cost("luck"), roulette.removal_cost("odds")
        self.assertGreater(common, 3 * legendary)
        self.assertGreaterEqual(common, 200)
        before = roulette.removal_cost("outs")
        roulette.remove("luck")
        self.assertGreater(roulette.removal_cost("outs"), before * 1.5)
        self.assertNotIn("luck", roulette.probabilities())
        self.assertAlmostEqual(sum(roulette.probabilities().values()), 1.0)

    def test_roulette_never_returns_removed(self):
        roulette = Roulette(10, random.Random(2))
        for key in ("luck", "peek", "swap"):
            roulette.remove(key)
        for _ in range(300):
            self.assertNotIn(roulette.spin().key, ("luck", "peek", "swap"))

    def test_legendary_is_rarest(self):
        probs = Roulette(10).probabilities()
        self.assertEqual(min(probs, key=probs.get), "odds")

    def test_peeked_card_is_the_next_board_card(self):
        session = TournamentSession("Eu", "easy", "low", random.Random(5))
        session.new_hand()
        hand = session.hand
        hand.lucky_seats.add(hand.index_of(session.human))
        result = NextCard().use(hand, session.human)
        while hand.to_act is not None:
            hand.act("call")
        hand.advance()
        self.assertEqual(hand.board[0], result.data["card"])

    def test_peek_not_allowed_on_river(self):
        session = TournamentSession("Eu", "easy", "low", random.Random(5))
        session.new_hand()
        session.hand.street = "river"
        ok, _ = NextCard().can_use(session.hand, session.human)
        self.assertFalse(ok)

    def test_deck_put_back_respects_lock(self):
        deck = Deck(random.Random(1))
        top = deck.peek()
        for _ in range(20):
            deck.put_back(Card(2, 0))
        self.assertEqual(deck.draw(), top)


class TournamentTest(unittest.TestCase):
    def test_blinds_go_up(self):
        t = TournamentSession("Eu", "easy", "low", random.Random(1))
        self.assertEqual(t.blinds(), t.LEVELS[0])
        t.hands_played = t.HANDS_PER_LEVEL
        self.assertEqual(t.blinds(), t.LEVELS[1])

    def test_prizes(self):
        t = TournamentSession("Eu", "easy", "low", random.Random(1))
        self.assertEqual(t.prize_for(1) + t.prize_for(2), t.prize_pool)
        self.assertEqual(t.prize_for(3), 0)


if __name__ == "__main__":
    unittest.main()
