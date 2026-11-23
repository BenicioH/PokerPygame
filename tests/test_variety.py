"""Testes das modalidades (Omaha, Pineapple) e dos mini games."""

import random
import unittest

from poker.engine import minigames
from poker.engine.bots import make_bot
from poker.engine.cards import Card
from poker.engine.evaluator import FLUSH, PAIR, STRAIGHT_FLUSH, TRIPS
from poker.engine.session import CashSession, TournamentSession
from poker.engine.variants import VARIANTS, best_discard

S, H, D, C = range(4)


def cards(*pairs):
    return [Card(rank, suit) for rank, suit in pairs]


class VariantTest(unittest.TestCase):
    def test_omaha_must_use_two_hole_cards(self):
        omaha = VARIANTS["omaha4"]
        board = cards((2, H), (7, H), (9, H), (12, H), (4, S))
        one_heart = cards((14, H), (3, C), (5, D), (8, S))
        self.assertNotEqual(omaha.best(one_heart, board)[0], FLUSH)
        self.assertEqual(VARIANTS["holdem"].best(one_heart[:2], board)[0], FLUSH)
        two_hearts = cards((14, H), (3, H), (5, D), (8, S))
        self.assertEqual(omaha.best(two_hearts, board)[0], FLUSH)

    def test_omaha_board_trips_need_two_hole_cards(self):
        omaha = VARIANTS["omaha4"]
        board = cards((9, S), (9, H), (9, D), (2, C), (5, S))
        hole = cards((14, S), (13, H), (7, D), (3, C))
        self.assertEqual(omaha.best(hole, board)[0], TRIPS)
        self.assertEqual(omaha.best(cards((14, S), (14, H), (7, D), (3, C)), board)[0], 6)

    def test_best_cards_omaha_uses_two_and_three(self):
        omaha = VARIANTS["omaha5"]
        board = cards((10, S), (11, S), (12, S), (2, D), (3, C))
        hole = cards((13, S), (14, S), (4, H), (5, H), (6, H))
        best = omaha.best_cards(hole, board)
        self.assertEqual(omaha.best(hole, board)[0], STRAIGHT_FLUSH)
        self.assertEqual(len([c for c in best if c in hole]), 2)

    def test_pineapple_discard_keeps_pair(self):
        hole = cards((8, S), (8, H), (3, C))
        self.assertEqual(best_discard(hole), 2)

    def test_every_variant_plays_full_hands(self):
        for key in VARIANTS:
            rng = random.Random(3)
            session = CashSession("Eu", 200, "easy", "low", rng)
            session.human.bot = make_bot("easy", rng)
            session.set_variant(key)
            for _ in range(6):
                if session.human.stack <= 0:
                    session.rebuy(200)
                session.new_hand()
                hand = session.hand
                total = sum(p.stack for p in session.players) + hand.pot
                self.assertTrue(all(len(p.hole) == VARIANTS[key].hole_cards for p in hand.players))
                steps = 0
                while not hand.finished:
                    steps += 1
                    self.assertLess(steps, 400)
                    if hand.awaiting_discard:
                        for p in list(hand.awaiting_discard):
                            hand.discard(p, best_discard(p.hole))
                    elif hand.to_act is None:
                        hand.advance()
                    else:
                        p = hand.current_player
                        hand.act(*p.bot.decide(hand, p))
                if key == "pineapple" and len(hand.board) >= 3:
                    self.assertTrue(all(len(p.hole) == 2 for p in hand.players if p.in_hand))
                self.assertEqual(sum(p.stack for p in session.players), total, key)
                session.end_hand()


class MiniGameTest(unittest.TestCase):
    def participants(self, humans=1, bots=3, difficulty="medium"):
        people = [{"seat": i, "name": f"H{i}", "bot": False, "difficulty": difficulty, "color": [0, 0, 0]}
                  for i in range(humans)]
        people += [{"seat": humans + i, "name": f"B{i}", "bot": True, "difficulty": difficulty, "color": [0, 0, 0]}
                   for i in range(bots)]
        return people

    def test_minigame_every_two_hands(self):
        t = TournamentSession("Eu", "easy", "low", random.Random(1))
        t.new_hand()
        t.hand.finished = True
        t.end_hand()
        self.assertFalse(t.minigame_due())
        t.new_hand()
        t.end_hand()
        self.assertTrue(t.minigame_due())
        keys = {t.next_minigame() for _ in range(3)}
        self.assertEqual(keys, set(minigames.GAME_KEYS))

    def test_fast_human_wins_climb(self):
        rnd = minigames.create_round("climb", self.participants(difficulty="hard"), 5)
        rnd.start(0.0)
        t = 0.0
        while not rnd.over:
            t += 0.05
            rnd.set_progress(0, t * 10, t)
            rnd.tick(t)
        self.assertEqual(rnd.winner(), 0)

    def test_idle_human_loses_race(self):
        rnd = minigames.create_round("race", self.participants(difficulty="easy"), 5)
        rnd.start(0.0)
        t = 0.0
        while not rnd.over:
            t += 0.1
            rnd.tick(t)
        self.assertNotEqual(rnd.winner(), 0)
        self.assertLessEqual(t, minigames.RACE_LIMIT + 0.2)

    def test_runner_trips_without_jump(self):
        runner = minigames.Runner()
        now = 0.0
        for i in range(12):
            now += 0.1
            runner.press("left" if i % 2 == 0 else "right", now)
        self.assertTrue(runner.stunned(now))
        jumper = minigames.Runner()
        now = 0.0
        for i in range(12):
            now += 0.1
            if i == 8:
                jumper.jump(now)
            jumper.press("left" if i % 2 == 0 else "right", now)
        self.assertFalse(jumper.stunned(now))
        self.assertEqual(jumper.pos, 12)

    def test_quiz_scores_speed(self):
        self.assertGreater(minigames.quiz_points(True, 1.0), minigames.quiz_points(True, 8.0))
        self.assertEqual(minigames.quiz_points(False, 1.0), 0)
        rnd = minigames.create_round("quiz", self.participants(), 9)
        rnd.start(0.0)
        t = 0.0
        while not rnd.over:
            if rnd.phase == "question" and 0 not in rnd.answers[rnd.index]:
                rnd.answer(0, rnd.questions[rnd.index]["correct"], t + 0.5)
            t += 0.1
            rnd.tick(t)
        self.assertGreaterEqual(rnd.totals[0], 3 * 180)
        self.assertEqual(len(rnd.questions), 3)
        self.assertLess(t, 3 * (minigames.QUIZ_TIME + minigames.QUIZ_REVEAL) + 1)


if __name__ == "__main__":
    unittest.main()
