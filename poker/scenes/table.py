"""Tela da mesa: controla o andamento das mãos, os bots, as ações do jogador e os power-ups."""

import random

import pygame

from .. import config as C
from ..engine.hand import STREET_NAMES
from ..engine.powerups import MAX_INVENTORY, SPIN_EVERY
from ..engine.session import STAKES
from ..ui import draw
from ..ui.effects import FloatText
from ..ui.table_view import BOARD_Y, TABLE_CENTER, TableView, hole_center
from ..ui.widgets import Button, Slider
from .base import ConfirmDialog, Scene

AFTER_HAND_DELAY = 2.8
SIDE = pygame.Rect(1070, 12, 198, 518)
BAR = pygame.Rect(0, 620, C.WIDTH, 100)
RAISE_PANEL = pygame.Rect(650, 540, 612, 74)


def slot_rect(i):
    """Retângulo do i-ésimo espaço de power-up na barra de baixo."""
    return pygame.Rect(16 + i * 152, 630, 142, 80)


class TableScene(Scene):
    """Uma sessão (cash ou torneio) em andamento."""

    def __init__(self, app, session):
        super().__init__(app)
        self.session = session
        self.view = TableView(session, app.sound)
        self.rng = random.Random()
        self.think = 0.8
        self.after = 0.0
        self.hand_closed = False
        self.left = False
        self.hover_slot = None
        self._clear_hand_info()
        self._build_buttons()
        self._start_hand()

    def _clear_hand_info(self):
        """Esquece o que era só da mão anterior (alvo escolhido, resultados de power-ups)."""
        self.turn_announced = False
        self.targeting = None
        self.peek = None
        self.info = None
        self.equities = None
        self.outs = None

    def _build_buttons(self):
        bb = self.session.blinds()[1]
        self.fold_btn = Button((650, 632, 160, 76), "Desistir", lambda: self._act("fold"), "danger", 28, pygame.K_f, sublabel="F")
        self.call_btn = Button((822, 632, 200, 76), "Passar", lambda: self._act("call"), "info", 28, pygame.K_c, sublabel="C")
        self.raise_btn = Button((1034, 632, 228, 76), "Aumentar", self._raise, "primary", 28, pygame.K_r, sublabel="R")
        self.quick = []
        for i, (label, frac) in enumerate((("Mín", 0), ("½ Pote", 0.5), ("¾ Pote", 0.75), ("Pote", 1.0), ("All-in", None))):
            self.quick.append(Button((RAISE_PANEL.left + 12 + i * 120, RAISE_PANEL.top + 8, 112, 28), label,
                                     lambda f=frac: self._quick_bet(f), "secondary", 21))
        self.slider = Slider((RAISE_PANEL.left + 22, RAISE_PANEL.top + 52, RAISE_PANEL.width - 44, 10), bb, bb, bb, bb)
        self.next_btn = Button((TABLE_CENTER[0] - 110, BOARD_Y + 110, 220, 46), "Próxima mão", self._next_hand,
                               "primary", 24, pygame.K_SPACE)
        self.pause_btn = Button((SIDE.left + 10, SIDE.top + 10, 86, 36), "Menu", self._pause, "secondary", 22)
        leave_label = "Desistir" if self.session.mode == "tournament" else "Sair"
        self.leave_btn = Button((SIDE.right - 96, SIDE.top + 10, 86, 36), leave_label, self._ask_leave, "danger", 22)
        self.buttons = [self.fold_btn, self.call_btn, self.raise_btn, *self.quick, self.next_btn,
                        self.pause_btn, self.leave_btn]

    def _human_turn(self):
        """Se é a vez do jogador e ele pode clicar nas ações agora."""
        hand = self.session.hand
        return (hand is not None and not hand.finished and hand.current_player is self.session.human
                and not self.view.busy and self.targeting is None)

    def _refresh_buttons(self):
        """Mostra só os botões que fazem sentido agora e atualiza os textos."""
        turn = self._human_turn()
        hand = self.session.hand
        legal = hand.legal() if turn else None
        self.fold_btn.visible = self.call_btn.visible = turn
        self.raise_btn.visible = bool(turn and legal.can_raise)
        for b in self.quick:
            b.visible = self.raise_btn.visible
        self.slider.visible = self.raise_btn.visible
        self.next_btn.visible = hand is not None and hand.finished and not self.view.busy
        if not turn:
            return
        if legal.can_check:
            self.call_btn.label = "Passar"
        elif legal.to_call >= self.session.human.stack:
            self.call_btn.label = f"All-in {draw.format_chips(legal.to_call)}"
        else:
            self.call_btn.label = f"Pagar {draw.format_chips(legal.to_call)}"
        value = self.slider.value
        if value >= legal.max_raise_to:
            self.raise_btn.label = f"All-in {draw.format_chips(value)}"
        elif hand.current_bet == 0:
            self.raise_btn.label = f"Apostar {draw.format_chips(value)}"
        else:
            self.raise_btn.label = f"Aumentar {draw.format_chips(value)}"

    def _act(self, kind, amount=0):
        """Faz a jogada do jogador (``fold``, ``call`` ou ``raise``)."""
        if not self._human_turn():
            return
        self.view.enqueue(self.session.hand.act(kind, amount))
        self.turn_announced = False
        self.think = 0.5

    def _raise(self):
        self._act("raise", self.slider.value)

    def _quick_bet(self, fraction):
        """Atalhos da aposta: 0 = mínimo, ``None`` = all-in, senão uma fração do pote."""
        hand = self.session.hand
        legal = hand.legal()
        if fraction is None:
            self.slider.set_value(legal.max_raise_to)
        elif fraction == 0:
            self.slider.set_value(legal.min_raise_to)
        else:
            self.slider.set_value(hand.current_bet + int(fraction * (hand.pot + legal.to_call)))

    def _start_hand(self):
        """Distribui uma mão nova."""
        self.view.reset_hand()
        self.view.log.append(f"--- Mão #{self.session.hands_played + 1} ---")
        self.view.enqueue(self.session.new_hand())
        self.hand_closed = False
        self.after = 0.0
        self.think = 0.9
        self._clear_hand_info()

    def _next_hand(self):
        """Fecha a mão atual e decide o que vem: roleta, fim de jogo ou mão nova."""
        s = self.session
        hand = s.hand
        if hand is None or not hand.finished or self.view.busy or self.left:
            return
        self.next_btn.visible = False
        blinds_before = s.blinds()
        s.end_hand()
        s.hand = None
        self.app.save["hands_played"] += 1
        if s.blinds() != blinds_before and not s.is_over():
            sb, bb = s.blinds()
            self.app.toasts.push(f"Blinds subiram para {sb}/{bb}!", C.WARNING)
        if s.mode == "cash" and s.human.stack <= 0:
            self._offer_rebuy()
            return
        if s.is_over():
            self._finish_tournament()
            return
        self._continue()

    def _continue(self):
        """Entre as mãos: roleta (se for a hora), depois mini game (se for a hora), depois a próxima mão."""
        if self.session.spin_due():
            from .roulette import LocalRoulette, RouletteScene
            self.app.push(RouletteScene(self.app, LocalRoulette(self.session), self._after_roulette))
        else:
            self._after_roulette()

    def _after_roulette(self):
        """Abre o mini game se for a hora; senão começa a próxima mão."""
        if self.session.minigame_due():
            from .minigame import LocalMiniGame, MiniGameScene
            control = LocalMiniGame(self.session, self.session.next_minigame())
            self.app.push(MiniGameScene(self.app, control, self._after_minigame))
        else:
            self._start_hand()

    def _after_minigame(self, variant_name, chooser):
        """Avisa a modalidade escolhida e começa a próxima mão."""
        self.app.toasts.push(f"{chooser} escolheu {variant_name} para as próximas mãos!", C.GOLD, 3.5)
        self._start_hand()

    def _offer_rebuy(self):
        """Sem fichas no cash: oferece recomprar com o saldo ou sair."""
        info = STAKES[self.session.stake]
        amount = min(self.app.save["bankroll"], info["bb"] * 100)
        if amount < info["min_buy"]:
            self.app.toasts.push("Você ficou sem fichas e sem saldo para recomprar.", C.DANGER)
            self._leave()
            return

        def rebuy():
            self.app.save["bankroll"] -= amount
            self.session.rebuy(amount)
            self.view.stacks[0] = amount
            self._continue()

        self.app.push(ConfirmDialog(self.app, "Sem fichas!", f"Recomprar {draw.format_chips(amount)} fichas do seu saldo?",
                                    rebuy, "Recomprar", danger=False, on_no=self._leave, no_label="Sair da mesa"))

    def _pause(self):
        """Abre o menu de pausa."""
        from .pause import PauseScene
        self.app.push(PauseScene(self.app, self))

    def _ask_leave(self):
        """Pede confirmação antes de sair do cash ou abandonar o torneio."""
        if self.session.mode == "cash":
            hand = self.session.hand
            msg = "Suas fichas voltam para o saldo."
            if hand and not hand.finished and self.session.human.in_hand:
                msg = "Você está no meio de uma mão: o que já apostou fica no pote. " + msg
            self.app.push(ConfirmDialog(self.app, "Sair da mesa?", msg, self._leave, "Sair"))
        else:
            self.app.push(ConfirmDialog(self.app, "Abandonar o torneio?", "Você perde o buy-in e sai sem prêmio.",
                                        self._forfeit, "Abandonar"))

    def _store(self):
        """Guarda no save os power-ups que sobraram."""
        self.app.save.store_inventory(self.session.inventory)

    def _leave(self):
        """Sai do cash game levando as fichas de volta para o saldo."""
        if self.left:
            return
        self.left = True
        s = self.session
        save = self.app.save
        chips = s.human.stack
        save["bankroll"] += chips
        save["best_cashout"] = max(save["best_cashout"], chips)
        self._store()
        from .results import ResultsScene
        lines = [
            ("Fichas finais", draw.format_chips(chips)),
            ("Mãos jogadas", str(s.stats["hands"])),
            ("Mãos ganhas", str(s.stats["won"])),
            ("Maior pote", draw.format_chips(s.stats["biggest_pot"])),
            ("Power-ups usados", str(s.stats["powerups_used"])),
        ]
        profit = chips - s.stats["start"] - s.stats["rebought"]
        self.app.replace(ResultsScene(self.app, "Você saiu da mesa", lines, profit))

    def _forfeit(self):
        """Abandona o torneio no meio: perde as fichas e não leva prêmio."""
        self.session.human.stack = 0
        self._finish_tournament(forfeit=True)

    def _finish_tournament(self, forfeit=False):
        """Fim do torneio: calcula a colocação, paga o prêmio e mostra o resultado."""
        if self.left:
            return
        self.left = True
        s = self.session
        save = self.app.save
        if forfeit:
            place = max(len(s.remaining()) + 1, 2)
            prize = 0
        else:
            place = s.place_of(s.human)
            prize = s.prize_for(place)
        save["bankroll"] += prize
        if place == 1:
            save["tournaments_won"] += 1
        self._store()
        from .results import ResultsScene
        title = "Campeão!" if place == 1 else f"Você terminou em {place}º lugar"
        lines = [
            ("Colocação", f"{place}º de 6"),
            ("Prêmio", draw.format_chips(prize)),
            ("Mãos jogadas", str(s.stats["hands"])),
            ("Maior pote", draw.format_chips(s.stats["biggest_pot"])),
            ("Power-ups usados", str(s.stats["powerups_used"])),
        ]
        self.app.sound.play("reward" if prize else "lose")
        self.app.replace(ResultsScene(self.app, title, lines, prize - s.buy_in))

    def on_quit(self):
        """Fechar a janela no meio do cash devolve as fichas ao saldo."""
        if self.left:
            return
        self.left = True
        if self.session.mode == "cash":
            self.app.save["bankroll"] += self.session.human.stack
        self._store()

    def _click_slot(self, i):
        """Clique no i-ésimo power-up: usa na hora ou pede para escolher o alvo."""
        s = self.session
        if i >= len(s.inventory):
            return
        pu = s.inventory[i]
        if self.view.busy:
            self.app.toasts.push("Espere a animação terminar.", C.WARNING, 1.4)
            return
        ok, why = pu.can_use(s.hand, s.human)
        if not ok:
            self.app.sound.play("error")
            self.app.toasts.push(why, C.DANGER)
            return
        if pu.target is None:
            self._apply(pu)
        else:
            self.targeting = pu
            hint = "uma das suas cartas" if pu.target == "own_card" else "um adversário"
            self.app.toasts.push(f"{pu.name}: clique em {hint} (botão direito cancela)", pu.color, 3.5)

    def _apply(self, pu, target=None):
        """Usa o power-up (modo local)."""
        self.targeting = None
        self._show_result(pu, self.session.use_powerup(pu, target))

    def _show_result(self, pu, result):
        """Mostra o resultado de um power-up (aviso, efeito e painel lateral)."""
        s = self.session
        if not result.ok:
            self.app.sound.play("error")
            self.app.toasts.push(result.message, C.DANGER)
            return
        self.app.sound.play("powerup")
        self.app.toasts.items = [t for t in self.app.toasts.items if not t[0].endswith("cancela)")]
        self.app.toasts.push(f"{pu.name}: {result.message}", pu.color, 3.2)
        self.view.floats.append(FloatText(pu.name, (TABLE_CENTER[0], 470), pu.color, 32))
        self.view.particles.burst((TABLE_CENTER[0], 470), [pu.color, (255, 255, 255)], 30, 200)
        data = result.data
        board_len = len(s.hand.board)
        self.info = (pu, result.message)
        if pu.key == "peek":
            self.peek = (data["card"], board_len)
        elif pu.key == "outs":
            self.outs = (data["outs"], data["chance"], board_len)
        elif pu.key == "odds":
            self.equities = (data["equities"], board_len)
        elif pu.key == "swap" and "events" in data:
            self.view.enqueue(data["events"])

    def _target_click(self, pos):
        """Clique durante a escolha do alvo: uma carta sua ou um adversário."""
        pu = self.targeting
        hand = self.session.hand
        if pu.target == "own_card":
            k = self._card_at(pos)
            if k is not None:
                self._apply(pu, k)
            return
        for p in hand.players:
            if p is not self.session.human and p.in_hand and TableView.seat_rect(p.seat).collidepoint(pos):
                self._apply(pu, p)
                return

    def _card_at(self, pos):
        """Índice da carta do jogador sob o mouse (a de cima, se estiverem sobrepostas)."""
        n = len(self.session.human.hole) if self.session.human else 0
        for k in reversed(range(n)):
            if TableView.human_card_rect(k, n).collidepoint(pos):
                return k
        return None

    def _must_discard(self):
        """Pineapple: se o jogador ainda precisa escolher a carta para descartar."""
        hand = self.session.hand
        return bool(hand and not hand.finished and hand.awaiting_discard
                    and self.session.human in hand.awaiting_discard and not self.view.busy)

    def _discard(self, k):
        """Descarta a carta ``k`` (modo local)."""
        self.view.enqueue(self.session.hand.discard(self.session.human, k))

    def handle_event(self, event):
        """Descarte, escolha de alvo, atalhos de teclado, power-ups e botões."""
        if self._must_discard() and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            k = self._card_at(event.pos)
            if k is not None:
                self._discard(k)
                return True
        if self.targeting is not None:
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or \
                    (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
                self.targeting = None
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._target_click(event.pos)
                return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._pause()
                return True
            if pygame.K_1 <= event.key <= pygame.K_4:
                self._click_slot(event.key - pygame.K_1)
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN) and self.slider.visible:
                step = self.session.blinds()[1] * (1 if event.key == pygame.K_UP else -1)
                self.slider.set_value(self.slider.value + step)
                return True
        if self.slider.visible and self.slider.handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(MAX_INVENTORY):
                if slot_rect(i).collidepoint(event.pos):
                    self._click_slot(i)
                    return True
        return super().handle_event(event)

    def update(self, dt):
        """Anima a mesa, faz o jogo andar e atualiza os botões."""
        super().update(dt)
        self.view.update(dt)
        pos = pygame.mouse.get_pos()
        self.hover_slot = next((i for i in range(MAX_INVENTORY) if slot_rect(i).collidepoint(pos)), None)
        if not self.left:
            self._drive(dt)
        if self.session.hand is not None and not self.left:
            self._refresh_buttons()

    def _drive(self, dt):
        """Faz o jogo andar: bots decidem, ruas abrem, mãos terminam (modo local)."""
        hand = self.session.hand
        if hand is None:
            return
        if not self.view.busy:
            self.view.sync()
            if hand.finished:
                if not self.hand_closed:
                    self.hand_closed = True
                    if hand.street == "showdown" and self.session.human.in_hand and \
                            all(p is not self.session.human for p, _, _ in hand.winners):
                        self.app.sound.play("lose")
                self.after += dt
                if self.after >= AFTER_HAND_DELAY:
                    self._next_hand()
            elif hand.awaiting_discard:
                self.think -= dt
                if self.think <= 0:
                    self.view.enqueue(self.session.bot_discards())
                    self.think = 0.6
            elif hand.to_act is None:
                self.view.enqueue(hand.advance())
            elif hand.current_player.is_human:
                if not self.turn_announced and self.targeting is None:
                    self.turn_announced = True
                    self.app.sound.play("turn")
                    legal = hand.legal()
                    self.slider.step = self.session.blinds()[1]
                    self.slider.set_range(legal.min_raise_to, legal.max_raise_to, legal.min_raise_to)
            else:
                self.think -= dt
                if self.think <= 0:
                    player = hand.current_player
                    kind, amount = player.bot.decide(hand, player)
                    self.view.enqueue(hand.act(kind, amount))
                    self.think = self.rng.uniform(0.5, 1.1)

    def draw(self, surface):
        """Mesa, painel lateral, barra de power-ups, botões e dicas."""
        surface.fill(C.BG)
        s = self.session
        hand = s.hand
        board_len = len(hand.board) if hand else 0
        pos = pygame.mouse.get_pos()
        extras = {
            "peek": self.peek,
            "equities": self.equities[0] if self.equities and self.equities[1] == board_len else None,
            "target": self.targeting.target if self.targeting else None,
            "hover_seat": next((p.seat for p in s.players if p and TableView.seat_rect(p.seat).collidepoint(pos)), None),
            "hover_card": self._card_at(pos) if s.human else None,
            "discard": self._must_discard(),
        }
        if hand:
            self.view.draw(surface, extras)
            self._draw_human_hand_name(surface, hand)
        self._draw_side(surface, board_len)
        self._draw_bar(surface)
        if self.raise_btn.visible:
            draw.panel(surface, RAISE_PANEL, C.PANEL, C.PANEL_BORDER, 12)
        super().draw(surface)
        self.slider.draw(surface)
        if self._must_discard():
            draw.text(surface, "Pineapple: clique na carta que vai descartar", (TABLE_CENTER[0], 160), 28, C.WARNING, True, "center")
        if self.targeting:
            hint = "Escolha uma das suas cartas" if self.targeting.target == "own_card" else "Escolha um adversário"
            draw.text(surface, hint, (TABLE_CENTER[0], 160), 28, self.targeting.color, True, "center")
        self._draw_tooltip(surface)

    def _draw_human_hand_name(self, surface, hand):
        """Nome da mão do jogador ao lado das cartas dele (e os power-ups ativos)."""
        human = self.session.human
        if not human or not human.in_hand:
            return
        n = len(human.hole)
        if self.view.hole_visible.get(0, 0) < n:
            return
        visible_board = hand.board[: self.view.board_visible]
        if len(visible_board) >= 3 or hand.variant.key in ("holdem", "pineapple"):
            name = hand.variant.hand_name(human.hole, visible_board)
        else:
            name = hand.variant.name
        x = hole_center(0, n - 1, n)[0] + 48
        effects = " • ".join(self.session.active_effects)
        draw.text(surface, name, (x, 500), 24, C.TEXT, True, "midleft")
        if effects:
            draw.text(surface, effects, (x, 524), 19, (200, 130, 255), False, "midleft")

    def _draw_side(self, surface, board_len):
        """Painel da direita: mesa, blinds, contagens, resultado de power-up e histórico."""
        s = self.session
        draw.panel(surface, SIDE, C.PANEL, C.PANEL_BORDER, 12)
        x = SIDE.left + 14
        y = SIDE.top + 60
        sb, bb = s.blinds()
        mode = {"cash": "Cash Game", "tournament": "Torneio"}[s.mode]
        draw.text(surface, mode, (x, y), 26, C.TEXT, True)
        y += 26
        draw.text(surface, f"{STAKES[s.stake]['label']} • Bots {C.DIFFICULTY_LABELS[s.difficulty]}", (x, y), 18, C.TEXT_DIM)
        y += 22
        draw.text(surface, f"Blinds {sb}/{bb}", (x, y), 22, C.GOLD, True)
        y += 22
        if s.mode == "tournament":
            draw.text(surface, f"Nível {s.level + 1} • sobe em {s.hands_to_next_level()} mãos", (x, y), 18, C.TEXT_DIM)
            y += 20
            draw.text(surface, f"Restam {len(s.remaining())} de 6", (x, y), 18, C.TEXT_DIM)
            y += 20
        hand = s.hand
        if hand:
            draw.text(surface, f"Mão #{s.hands_played + 1} • {STREET_NAMES.get(hand.street, '')}", (x, y), 18, C.TEXT_DIM)
            y += 20
        draw.text(surface, s.variant.name, (x, y), 18, C.WARNING)
        y += 20
        hands_left = max(0, s.hands_until_minigame)
        if hands_left == 0:
            minigame_text = "Mini game agora"
        elif hands_left == 1:
            minigame_text = "Mini game em 1 mão"
        else:
            minigame_text = f"Mini game em {hands_left} mãos"
        draw.text(surface, minigame_text, (x, y), 18, C.TEXT_DIM)
        y += 24

        draw.text(surface, "Roleta de power-ups", (x, y), 20, C.TEXT, True)
        y += 22
        if s.hands_until_spin < 0:
            draw.text(surface, "Desligada nesta mesa", (x, y), 18, C.TEXT_FAINT)
        elif len(s.inventory) >= MAX_INVENTORY:
            draw.text(surface, "Inventário cheio", (x, y), 18, C.WARNING)
        else:
            done = SPIN_EVERY - s.hands_until_spin
            for k in range(SPIN_EVERY):
                color = C.ACCENT if k < done else C.BG_DARK
                pygame.draw.rect(surface, color, (x + k * 40, y + 2, 34, 10), border_radius=5)
            draw.text(surface, f"em {s.hands_until_spin}", (x + 126, y - 3), 18, C.TEXT_DIM)
        y += 26

        info_rect = pygame.Rect(SIDE.left + 8, y, SIDE.width - 16, 150)
        draw.panel(surface, info_rect, C.BG_DARK, None, 8)
        self._draw_powerup_info(surface, info_rect, board_len)
        y = info_rect.bottom + 10

        draw.text(surface, "Histórico", (x, y), 20, C.TEXT, True)
        y += 22
        max_lines = (SIDE.bottom - y - 8) // 17
        lines = []
        for entry in self.view.log[-max_lines:]:
            lines += draw.wrap(entry, 18, SIDE.width - 28)
        for i, line in enumerate(lines[-max_lines:]):
            draw.text(surface, line, (x, y + i * 17), 18, C.TEXT_DIM)

    def _draw_powerup_info(self, surface, rect, board_len):
        """Caixa do painel lateral com o resultado do último power-up (ou uma dica)."""
        x, y = rect.left + 8, rect.top + 6
        if self.outs and self.outs[2] == board_len:
            outs, chance, _ = self.outs
            draw.text(surface, f"Outs: {len(outs)} ({chance:.0%})", (x, y), 20, (110, 230, 140), True)
            for i, (card, _) in enumerate(outs[:18]):
                cx = x + 14 + (i % 6) * 30
                cy = y + 46 + (i // 6) * 40
                draw.draw_card(surface, card, (cx, cy), 28, 38)
            if len(outs) > 18:
                draw.text(surface, f"+{len(outs) - 18}", (rect.right - 8, rect.bottom - 6), 18, C.TEXT_DIM, False, "bottomright")
            if not outs:
                draw.text(surface, "Nenhuma carta melhora a sua mão.", (x, y + 30), 18, C.TEXT_DIM)
            return
        if self.equities and self.equities[1] == board_len:
            draw.text(surface, "Oráculo", (x, y), 20, C.GOLD, True)
            for i, (seat, eq) in enumerate(sorted(self.equities[0].items(), key=lambda kv: -kv[1])[:6]):
                name = self.session.players[seat].name
                color = C.ACCENT if seat == 0 else C.TEXT
                draw.text(surface, name, (x, y + 24 + i * 20), 19, color)
                draw.text(surface, f"{eq:.0%}", (rect.right - 10, y + 24 + i * 20), 19, color, True, "topright")
            return
        if self.info:
            pu, message = self.info
            draw.text(surface, pu.name, (x, y), 20, pu.color, True)
            draw.text_block(surface, message, pygame.Rect(x, y + 26, rect.width - 16, 110), 19, C.TEXT_DIM)
            return
        draw.text(surface, "Power-ups", (x, y), 20, C.TEXT, True)
        draw.text_block(surface, "Use com clique ou com as teclas 1 a 4. O resultado aparece aqui.",
                        pygame.Rect(x, y + 26, rect.width - 16, 110), 18, C.TEXT_FAINT)

    def _draw_bar(self, surface):
        """Barra de baixo com os 4 espaços de power-up e de quem é a vez."""
        pygame.draw.rect(surface, C.BG_DARK, BAR)
        pygame.draw.line(surface, C.PANEL_BORDER, BAR.topleft, BAR.topright, 2)
        s = self.session
        for i in range(MAX_INVENTORY):
            rect = slot_rect(i)
            if i < len(s.inventory):
                pu = s.inventory[i]
                usable = pu.can_use(s.hand, s.human)[0] if s.hand else False
                hover = self.hover_slot == i
                draw.panel(surface, rect, C.PANEL_LIGHT if hover else C.PANEL, pu.color if usable else C.PANEL_BORDER, 10)
                draw.powerup_icon(surface, pu, (rect.left + 24, rect.top + 25), 16, usable)
                draw.text(surface, pu.rarity[0], (rect.left + 48, rect.top + 25), 19, pu.color, False, "midleft")
                size = 22 if draw.font(22, True).size(pu.name)[0] < rect.width - 16 else 19
                draw.text(surface, pu.name, (rect.left + 10, rect.top + 58), size, C.TEXT if usable else C.TEXT_DIM, True, "midleft")
                draw.text(surface, str(i + 1), (rect.right - 8, rect.bottom - 6), 18, C.TEXT_FAINT, False, "bottomright")
            else:
                draw.panel(surface, rect, C.BG_DARK, C.PANEL, 10)
                draw.text(surface, "vazio", rect.center, 20, C.TEXT_FAINT, False, "center")
        if not self.fold_btn.visible:
            hand = s.hand
            message = ""
            if hand and not hand.finished and not s.human.in_hand:
                message = "Você desistiu desta mão"
            elif hand and not hand.finished and hand.current_player is not None and not hand.current_player.is_human:
                message = f"Vez de {hand.current_player.name}"
            if message:
                draw.text(surface, message, (956, 670), 26, C.TEXT_DIM, False, "center")

    def _draw_tooltip(self, surface):
        """Descrição do power-up sob o mouse (e por que não dá para usar agora)."""
        s = self.session
        if self.hover_slot is None or self.hover_slot >= len(s.inventory):
            return
        pu = s.inventory[self.hover_slot]
        rect = pygame.Rect(slot_rect(self.hover_slot).left, 0, 330, 0)
        lines = draw.wrap(pu.description, 20, rect.width - 24)
        why = pu.can_use(s.hand, s.human)[1] if s.hand else ""
        rect.height = 46 + len(lines) * 20 + (24 if why else 0)
        rect.bottom = BAR.top - 8
        draw.panel(surface, rect, C.PANEL, pu.color, 10)
        draw.text(surface, f"{pu.name} ({pu.rarity[0]})", (rect.left + 12, rect.top + 10), 22, pu.color, True)
        for i, line in enumerate(lines):
            draw.text(surface, line, (rect.left + 12, rect.top + 36 + i * 20), 20, C.TEXT)
        if why:
            draw.text(surface, why, (rect.left + 12, rect.bottom - 26), 19, C.DANGER)
