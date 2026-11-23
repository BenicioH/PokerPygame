"""Tela dos mini games (Escalada, Corrida e Quiz) e da escolha da modalidade.

Como a roleta, a tela conversa com um "controle": :class:`LocalMiniGame`,
que roda a disputa neste computador (jogo contra bots).

Fases da tela: ``intro`` (regras e contagem 3-2-1) -> ``play`` -> ``results``
(classificação) -> ``choose`` (se você venceu, escolhe a modalidade) ou
``waiting`` (o vencedor está escolhendo) -> ``announce`` -> fecha.
"""

import math
import random
import time

import pygame

from .. import config as C
from ..engine import minigames as mg
from ..engine.variants import VARIANTS
from ..ui import draw
from ..ui.effects import Particles
from ..ui.widgets import Button
from .base import Scene

INTRO_TIME = 3.5
RESULTS_TIME = 3.0
ANNOUNCE_TIME = 2.2
BOT_CHOICE_DELAY = 1.5
PANEL = pygame.Rect(40, 30, C.WIDTH - 80, C.HEIGHT - 60)


class LocalMiniGame:
    """Controle do mini game no jogo contra bots."""

    def __init__(self, session, key):
        self.session = session
        self.key = key
        self.me = session.human.seat
        self.participants = [{"seat": seat, "name": name, "bot": bot, "difficulty": diff, "color": list(color)}
                             for seat, name, bot, diff, color in session.minigame_players()]
        self.round = mg.create_round(key, self.participants, random.randrange(1 << 30))
        self.choice = None
        self.over_at = None

    def start_play(self):
        """Começa a disputa (fim da contagem 3-2-1)."""
        self.round.start(time.monotonic())

    def update(self):
        """Avança a disputa e, se um bot venceu, faz ele escolher a modalidade."""
        now = time.monotonic()
        self.round.tick(now)
        if self.round.over and self.over_at is None:
            self.over_at = now
        if self.round.over and self.choice is None and not self.winner_is_me() \
                and now - self.over_at >= RESULTS_TIME + BOT_CHOICE_DELAY:
            winner = self.name_of(self.winner())
            key = random.choice([k for k in VARIANTS if k != self.session.variant.key])
            self.session.set_variant(key)
            self.choice = (key, winner)

    def state(self):
        """Estado atual para desenhar (progresso, tempo, pergunta do quiz...)."""
        return self.round.state(time.monotonic())

    @property
    def over(self):
        """Se a disputa acabou."""
        return self.round.over

    def standings(self):
        """Classificação final: lista de ``(assento, texto do resultado)``."""
        return self.round.standings()

    def winner(self):
        """Assento de quem venceu."""
        return self.round.winner()

    def winner_is_me(self):
        """Se o jogador venceu."""
        return self.winner() == self.me

    def send_progress(self, value):
        """Progresso do jogador na escalada ou na corrida."""
        self.round.set_progress(self.me, value, time.monotonic())

    def send_answer(self, choice):
        """Resposta do jogador no quiz."""
        self.round.answer(self.me, choice, time.monotonic())

    def choose(self, key):
        """O jogador venceu e escolheu a modalidade."""
        self.session.set_variant(key)
        self.choice = (key, "Você")

    def name_of(self, seat):
        """Nome de quem está no assento."""
        return next((p["name"] for p in self.participants if p["seat"] == seat), "?")

    def color_of(self, seat):
        """Cor de quem está no assento."""
        return tuple(next((p["color"] for p in self.participants if p["seat"] == seat), (120, 120, 120)))

    def current_variant(self):
        """Chave da modalidade em jogo agora."""
        return self.session.variant.key


class MiniGameScene(Scene):
    """Disputa entre as mãos. ``on_done(nome_da_modalidade, quem_escolheu)`` é chamado no fim."""

    overlay = True

    def __init__(self, app, control, on_done):
        super().__init__(app)
        self.control = control
        self.on_done = on_done
        self.phase = "intro"
        self.timer = 0.0
        self.time = 0.0
        self.presses = 0
        self.runner = mg.Runner()
        self.answered_index = -1
        self.my_choice = None
        self.particles = Particles()
        self.last_count = 4
        self.title, self.instructions = mg.GAME_INFO[control.key]

    def handle_event(self, event):
        """Durante a disputa as teclas vão para o mini game; nas outras fases, para os botões."""
        if self.phase != "play":
            return super().handle_event(event)
        if self.control.key == "climb":
            self._climb_input(event)
        elif self.control.key == "race":
            self._race_input(event)
        else:
            self._quiz_input(event)
        return True

    def _climb_input(self, event):
        """Escalada: cada ESPAÇO sobe um andar."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and self.presses < mg.CLIMB_GOAL:
            self.presses += 1
            self.control.send_progress(self.presses)
            if self.presses % 4 == 0:
                self.app.sound.play("tick")

    def _race_input(self, event):
        """Corrida: alternar ESQUERDA e DIREITA corre; CIMA pula a barreira."""
        if event.type != pygame.KEYDOWN:
            return
        now = time.monotonic()
        before = self.runner.pos
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.runner.press("left", now)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.runner.press("right", now)
        elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
            self.runner.jump(now)
            self.app.sound.play("click")
        if self.runner.pos != before:
            self.control.send_progress(self.runner.pos)
            if self.runner.stunned(now):
                self.app.sound.play("error")

    def _quiz_input(self, event):
        """Quiz: teclas 1 a 4 ou clique numa opção (uma resposta por pergunta)."""
        choice = None
        if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_4:
            choice = event.key - pygame.K_1
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            choice = next((i for i in range(4) if self._option_rect(i).collidepoint(event.pos)), None)
        if choice is None:
            return
        state = self.control.state()
        if state["phase"] == "question" and self.answered_index != state["index"]:
            self.answered_index = state["index"]
            self.my_choice = choice
            self.control.send_answer(choice)
            self.app.sound.play("click")

    def update(self, dt):
        """Passa de uma fase para a outra quando chega a hora."""
        super().update(dt)
        self.time += dt
        self.timer += dt
        self.particles.update(dt)
        self.control.update()
        if self.phase == "intro":
            count = int(INTRO_TIME - self.timer) + 1
            if count != self.last_count and count <= 3:
                self.last_count = count
                self.app.sound.play("tick")
            if self.timer >= INTRO_TIME:
                self.phase = "play"
                self.timer = 0.0
                self.control.start_play()
                self.app.sound.play("turn")
        elif self.phase == "play":
            if self.control.over:
                self.phase = "results"
                self.timer = 0.0
                if self.control.winner_is_me():
                    self.app.sound.play("reward")
                    self.particles.burst((C.WIDTH // 2, 200), [C.GOLD, C.ACCENT, (255, 255, 255)], 70, 320)
                else:
                    self.app.sound.play("lose")
        elif self.phase == "results":
            if self.timer >= RESULTS_TIME:
                self.timer = 0.0
                if self.control.winner_is_me():
                    self.phase = "choose"
                    self._build_choice()
                else:
                    self.phase = "waiting"
        elif self.phase in ("choose", "waiting"):
            if self.control.choice is not None:
                self.phase = "announce"
                self.timer = 0.0
                self.buttons = []
                self.app.sound.play("powerup")
        elif self.phase == "announce" and self.timer >= ANNOUNCE_TIME:
            key, who = self.control.choice
            self.app.pop()
            self.on_done(VARIANTS[key].name, who)

    def _build_choice(self):
        """Um botão para cada modalidade (a atual fica marcada)."""
        self.buttons = []
        current = self.control.current_variant()
        for i, (key, variant) in enumerate(VARIANTS.items()):
            col, row = i % 3, i // 3
            rect = (PANEL.left + 70 + col * 370, PANEL.top + 190 + row * 170, 340, 70)
            label = variant.name + (" (atual)" if key == current else "")
            self.buttons.append(Button(rect, label, lambda k=key: self._choose(k), "primary" if key != current else "secondary", 30))

    def _choose(self, key):
        """Clique numa modalidade (só vale o primeiro)."""
        if self.control.choice is None:
            self.control.choose(key)

    def draw(self, surface):
        """Painel do mini game com o conteúdo da fase atual."""
        draw.alpha_rect(surface, surface.get_rect(), (0, 0, 0), 190)
        draw.panel(surface, PANEL, C.BG, C.WARNING, 18, 3)
        draw.text(surface, f"MINI GAME: {self.title.upper()}", (PANEL.centerx, PANEL.top + 34), 40, C.WARNING, True, "center")
        if self.phase == "intro":
            self._draw_intro(surface)
        elif self.phase == "play":
            if self.control.key == "climb":
                self._draw_climb(surface)
            elif self.control.key == "race":
                self._draw_race(surface)
            else:
                self._draw_quiz(surface)
        elif self.phase == "results":
            self._draw_results(surface)
        elif self.phase == "choose":
            draw.text(surface, "Você venceu! Escolha a modalidade das próximas mãos:", (PANEL.centerx, PANEL.top + 110),
                      30, C.GOLD, True, "center")
            for i, (key, variant) in enumerate(VARIANTS.items()):
                col, row = i % 3, i // 3
                rect = pygame.Rect(PANEL.left + 70 + col * 370, PANEL.top + 266 + row * 170, 340, 80)
                draw.text_block(surface, variant.description, rect, 20, C.TEXT_DIM, 2)
        elif self.phase == "waiting":
            name = self.control.name_of(self.control.winner())
            pulse = "." * (int(self.time * 3) % 4)
            draw.text(surface, f"{name} venceu e está escolhendo a modalidade{pulse}", (PANEL.centerx, PANEL.centery),
                      34, C.TEXT, True, "center")
        elif self.phase == "announce":
            key, who = self.control.choice
            draw.text(surface, f"{who} escolheu", (PANEL.centerx, PANEL.centery - 50), 34, C.TEXT_DIM, False, "center")
            draw.text(surface, VARIANTS[key].name, (PANEL.centerx, PANEL.centery + 10), 64, C.GOLD, True, "center")
            draw.text(surface, VARIANTS[key].description, (PANEL.centerx, PANEL.centery + 70), 24, C.TEXT, False, "center")
        self.particles.draw(surface)
        super().draw(surface)

    def _draw_intro(self, surface):
        """Regras, participantes e a contagem 3-2-1 crescendo a cada número."""
        draw.text_block(surface, self.instructions, pygame.Rect(PANEL.left + 120, PANEL.top + 110, PANEL.width - 240, 100),
                        32, C.TEXT, 8)
        draw.text(surface, "Quem vencer escolhe a modalidade das próximas mãos!", (PANEL.centerx, PANEL.top + 230),
                  26, C.GOLD, False, "center")
        names = "  •  ".join(p["name"] for p in self.control.participants)
        draw.text(surface, names, (PANEL.centerx, PANEL.top + 280), 24, C.TEXT_DIM, False, "center")
        count = max(1, int(INTRO_TIME - self.timer) + 1)
        scale = 1 + 0.3 * (1 - (INTRO_TIME - self.timer) % 1)
        draw.text(surface, str(min(3, count)), (PANEL.centerx, PANEL.centery + 120), int(110 * scale), C.ACCENT, True, "center")

    def _participant_progress(self, state):
        """Progresso de cada um; o seu vem direto do teclado (mais suave)."""
        values = {seat: value for seat, value in state["progress"]}
        mine = self.presses if self.control.key == "climb" else self.runner.pos
        values[self.control.me] = max(values.get(self.control.me, 0), mine)
        return values, {seat: t for seat, t in state["finish"]}

    def _draw_timer(self, surface, left, total):
        """Barra do tempo que resta (fica vermelha no fim)."""
        bar = pygame.Rect(PANEL.left + 40, PANEL.top + 66, PANEL.width - 80, 10)
        pygame.draw.rect(surface, C.PANEL, bar, border_radius=5)
        fill = bar.copy()
        fill.width = int(bar.width * max(0.0, min(1.0, left / total)))
        pygame.draw.rect(surface, C.ACCENT if left > total * 0.3 else C.DANGER, fill, border_radius=5)

    def _draw_climb(self, surface):
        """Um prédio por participante, com a bolinha subindo."""
        state = self.control.state()
        self._draw_timer(surface, state["time_left"], mg.CLIMB_LIMIT)
        values, finish = self._participant_progress(state)
        people = self.control.participants
        width = (PANEL.width - 80) // len(people)
        base = PANEL.bottom - 70
        height = 430
        for i, p in enumerate(people):
            seat = p["seat"]
            x = PANEL.left + 40 + i * width + width // 2
            mine = seat == self.control.me
            building = pygame.Rect(0, 0, min(120, width - 30), height)
            building.midbottom = (x, base)
            pygame.draw.rect(surface, (44, 58, 74) if not mine else (52, 76, 70), building, border_radius=4)
            for floor in range(12):
                for col in range(3):
                    window = pygame.Rect(building.left + 14 + col * (building.width - 28) // 3, building.top + 12 + floor * 34,
                                         (building.width - 28) // 3 - 8, 18)
                    lit = (floor * 3 + col + i) % 4 == 0
                    pygame.draw.rect(surface, (230, 200, 90) if lit else (30, 40, 52), window, border_radius=2)
            progress = values.get(seat, 0) / mg.CLIMB_GOAL
            y = base - progress * (height - 20) - 18
            wobble = math.sin(self.time * 18 + i) * 3 if progress < 1 else 0
            pygame.draw.circle(surface, tuple(p["color"]), (int(x + wobble), int(y)), 18)
            draw.text(surface, p["name"][0].upper(), (x + wobble, y), 24, C.BG, True, "center")
            if seat in finish:
                draw.text(surface, f"{finish[seat]:.1f}s", (x, building.top - 40), 24, C.GOLD, True, "center")
            draw.text(surface, self._label(p["name"], mine), (x, base + 22), 22,
                      C.ACCENT if mine else C.TEXT, True, "center")
        if self.presses < mg.CLIMB_GOAL:
            pulse = 0.5 + 0.5 * math.sin(self.time * 10)
            draw.text(surface, "ESPAÇO! ESPAÇO!", (PANEL.centerx, PANEL.top + 104), 34,
                      draw.lerp_color(C.WARNING, C.TEXT, pulse), True, "center")

    def _draw_race(self, surface):
        """Uma pista por participante, com as barreiras vermelhas."""
        state = self.control.state()
        self._draw_timer(surface, state["time_left"], mg.RACE_LIMIT)
        values, finish = self._participant_progress(state)
        people = self.control.participants
        left, right = PANEL.left + 170, PANEL.right - 60
        lane_h = min(80, (PANEL.height - 170) // len(people))
        now = time.monotonic()
        for i, p in enumerate(people):
            seat = p["seat"]
            mine = seat == self.control.me
            y = PANEL.top + 130 + i * lane_h + lane_h // 2
            lane = pygame.Rect(left - 20, y - lane_h // 2 + 4, right - left + 40, lane_h - 8)
            pygame.draw.rect(surface, (52, 76, 70) if mine else C.PANEL, lane, border_radius=8)
            draw.text(surface, p["name"], (left - 34, y), 22, C.ACCENT if mine else C.TEXT, True, "midright")
            for h in mg.HURDLES:
                hx = left + (right - left) * h / mg.RACE_GOAL
                pygame.draw.rect(surface, C.DANGER, (hx - 3, y - 14, 6, 28), border_radius=2)
            pygame.draw.line(surface, C.TEXT, (right, lane.top + 4), (right, lane.bottom - 4), 3)
            pos = values.get(seat, 0) / mg.RACE_GOAL
            x = left + (right - left) * pos
            hop = 0
            if mine and self.runner.airborne(now):
                hop = -math.sin((self.runner.air_until - now) / mg.AIR_TIME * math.pi) * 22
            elif pos < 1:
                hop = -abs(math.sin(self.time * 12 + i)) * 4
            pygame.draw.circle(surface, tuple(p["color"]), (int(x), int(y + hop)), 15)
            draw.text(surface, p["name"][0].upper(), (x, y + hop), 22, C.BG, True, "center")
            if mine and self.runner.stunned(now):
                draw.text(surface, "tonto!", (x, y - 26), 20, C.WARNING, True, "center")
            if seat in finish:
                draw.text(surface, f"{finish[seat]:.1f}s", (right + 8, y), 20, C.GOLD, True, "midleft")
        draw.text(surface, "Alterne ESQUERDA e DIREITA  •  CIMA pula as barreiras vermelhas",
                  (PANEL.centerx, PANEL.top + 100), 24, C.WARNING, True, "center")

    @staticmethod
    def _label(name, mine):
        """Nome com "(você)" para o próprio jogador (sem repetir se o nome já é "Você")."""
        return f"{name} (você)" if mine and name.lower() != "você" else name

    def _option_rect(self, i):
        """Retângulo da i-ésima opção do quiz (grade 2 x 2)."""
        col, row = i % 2, i // 2
        return pygame.Rect(PANEL.left + 60 + col * 450, PANEL.top + 250 + row * 110, 430, 92)

    def _draw_quiz(self, surface):
        """Pergunta, as 4 opções (verde/vermelho na revelação) e o placar."""
        state = self.control.state()
        total = mg.QUIZ_TIME if state["phase"] == "question" else mg.QUIZ_REVEAL
        self._draw_timer(surface, state["time_left"], total)
        draw.text(surface, f"Pergunta {state['index'] + 1} de {mg.QUIZ_QUESTIONS}", (PANEL.left + 60, PANEL.top + 96), 24, C.TEXT_DIM)
        draw.text(surface, f"{state['time_left']:.0f}s", (PANEL.left + 960, PANEL.top + 96), 28, C.WARNING, True, "topright")
        draw.text_block(surface, state["text"], pygame.Rect(PANEL.left + 60, PANEL.top + 140, 900, 100), 36, C.TEXT, 6)
        mine_this = self.answered_index == state["index"]
        for i, option in enumerate(state["options"]):
            rect = self._option_rect(i)
            color, border = C.PANEL, C.PANEL_BORDER
            if state["phase"] == "reveal":
                if i == state.get("correct"):
                    color, border = (30, 110, 60), C.ACCENT
                elif mine_this and i == self.my_choice:
                    color, border = (120, 40, 40), C.DANGER
            elif mine_this and i == self.my_choice:
                border = C.INFO
            elif rect.collidepoint(pygame.mouse.get_pos()) and not mine_this:
                color = C.PANEL_LIGHT
            draw.panel(surface, rect, color, border, 12, 3)
            draw.text(surface, str(i + 1), (rect.left + 28, rect.centery), 34, C.WARNING, True, "center")
            draw.text_block(surface, option, pygame.Rect(rect.left + 56, rect.top + 18, rect.width - 70, 70), 28, C.TEXT, 2)
        board = pygame.Rect(PANEL.right - 230, PANEL.top + 130, 200, 380)
        draw.panel(surface, board, C.PANEL, C.PANEL_BORDER, 12)
        draw.text(surface, "Placar", (board.left + 14, board.top + 12), 24, C.TEXT, True)
        totals = dict(state["totals"])
        answered = set(state["answered"])
        picks = {seat: (choice, pts) for seat, choice, pts in state.get("picks", [])}
        ordered = sorted(self.control.participants, key=lambda p: -totals.get(p["seat"], 0))
        for i, p in enumerate(ordered):
            seat = p["seat"]
            y = board.top + 52 + i * 52
            mine = seat == self.control.me
            draw.text(surface, p["name"], (board.left + 14, y), 21, C.ACCENT if mine else C.TEXT, True)
            draw.text(surface, f"{totals.get(seat, 0)} pts", (board.left + 14, y + 22), 19, C.GOLD)
            if state["phase"] == "reveal" and seat in picks:
                gained = picks[seat][1]
                draw.text(surface, f"+{gained}" if gained else "errou", (board.right - 12, y + 10), 20,
                          C.ACCENT if gained else C.DANGER, True, "topright")
            elif seat in answered:
                draw.text(surface, "respondeu", (board.right - 12, y + 10), 18, C.INFO, False, "topright")

    def _draw_results(self, surface):
        """Classificação com medalhas para os três primeiros."""
        standings = self.control.standings()
        draw.text(surface, "Resultado", (PANEL.centerx, PANEL.top + 100), 34, C.TEXT, True, "center")
        medals = [C.GOLD, (200, 205, 215), (205, 127, 50)]
        for i, (seat, label) in enumerate(standings):
            y = PANEL.top + 160 + i * 62
            rect = pygame.Rect(PANEL.centerx - 300, y, 600, 54)
            mine = seat == self.control.me
            draw.panel(surface, rect, C.PANEL_LIGHT if mine else C.PANEL, medals[i] if i < 3 else C.PANEL_BORDER, 10)
            draw.text(surface, f"{i + 1}º", (rect.left + 24, rect.centery), 30, medals[i] if i < 3 else C.TEXT_DIM, True, "midleft")
            pygame.draw.circle(surface, self.control.color_of(seat), (rect.left + 96, rect.centery), 16)
            draw.text(surface, self._label(self.control.name_of(seat), mine), (rect.left + 124, rect.centery),
                      28, C.TEXT, True, "midleft")
            draw.text(surface, label, (rect.right - 24, rect.centery), 28, C.GOLD, True, "midright")
