"""Desenho da mesa de poker e animação dos eventos da mão.

O motor (:mod:`poker.engine.hand`) muda o estado na hora. A :class:`TableView`
guarda uma cópia "atrasada" do que deve aparecer na tela (fichas, apostas,
cartas visíveis) e só a atualiza enquanto anima cada evento. Assim as cartas
voam até os jogadores, as fichas vão para o pote e o vencedor recebe o pote
na ordem certa, mesmo que o motor já tenha terminado a jogada.
"""

import math
from collections import deque

import pygame

from .. import config as C
from . import draw
from .effects import Flight, FloatText, Particles

TABLE_CENTER = (540, 330)
FELT_RECT = pygame.Rect(0, 0, 860, 420)
FELT_RECT.center = TABLE_CENTER
DECK_POS = (540, 200)
POT_POS = (540, 245)
BOARD_Y = 322
BOARD_CARD = (62, 88)
HOLE_CARD = (46, 66)
HUMAN_CARD = (70, 100)

SEAT_POS = {0: (540, 575), 1: (175, 465), 2: (175, 195), 3: (540, 108), 4: (905, 195), 5: (905, 465)}
BET_POS = {0: (540, 405), 1: (305, 420), 2: (305, 245), 3: (540, 185), 4: (775, 245), 5: (775, 420)}
SEAT_SIZE = (184, 58)
EVENT_PAUSE = {
    "blind": 0.15, "deal": 0.1, "action": 0.45, "collect": 0.45, "board": 0.35,
    "lucky": 0.7, "reveal": 0.7, "showdown": 0.9, "win": 1.0, "shield": 0.8, "swap": 0.5,
}

ACTION_LABELS = {
    "Fold": "Desistiu", "Check": "Passou", "Call": "Pagou", "Raise": "Aumentou",
    "Bet": "Apostou", "All-in": "ALL-IN", "SB": "Small blind", "BB": "Big blind",
}


def known_hand_name(hand, hole):
    """Nome da mão de ``hole`` na modalidade da mão, ou "" se alguma carta for desconhecida."""
    if not hole or any(card is None for card in hole):
        return ""
    return hand.variant.hand_name(hole, hand.board)


def board_slot(i):
    """Centro do espaço da i-ésima carta comunitária."""
    return (TABLE_CENTER[0] + (i - 2) * (BOARD_CARD[0] + 10), BOARD_Y)


HUMAN_SPACING = {1: 76, 2: 76, 3: 62, 4: 52, 5: 44, 6: 38}
OTHER_SPACING = {1: 32, 2: 32, 3: 26, 4: 22, 5: 19, 6: 17}


def hole_center(seat, k, n=2):
    """Centro da k-ésima de ``n`` cartas fechadas de um assento."""
    x, y = SEAT_POS[seat]
    offset = k - (n - 1) / 2
    if seat == 0:
        return (x + offset * HUMAN_SPACING.get(n, 38), y - 88)
    return (x + offset * OTHER_SPACING.get(n, 17), y - 50)


class TableView:
    """Estado visual da mesa e a fila de eventos a animar."""

    def __init__(self, session, sound):
        self.session = session
        self.sound = sound
        self.queue = deque()
        self.wait = 0.0
        self.flights = []
        self.floats = []
        self.particles = Particles()
        self.time = 0.0
        self.log = []
        self.reset_hand()

    def reset_hand(self):
        """Zera o que é exibido no começo de uma mão."""
        self.stacks = {p.seat: p.stack for p in self.session.players if p}
        self.bets = {}
        self.pot = 0
        self.hole_visible = {}
        self.board_visible = 0
        self.board_flip = {}
        self.reveal = False
        self.winners = {}
        self.banner = ""
        self.shown_hand_names = False
        self._best_cache = {}

    def sync(self):
        """Copia o estado do motor quando não há nada animando."""
        hand = self.session.hand
        for p in self.session.players:
            if p:
                self.stacks[p.seat] = p.stack
        if hand is None:
            return
        self.bets = {p.seat: p.bet for p in hand.players if p.bet}
        self.pot = 0 if hand.finished else hand.collected_pot
        for p in hand.players:
            self.hole_visible[p.seat] = len(p.hole) if p.in_hand else 0
        for i in range(self.board_visible, len(hand.board)):
            self.board_flip[i] = 1.0
        self.board_visible = len(hand.board)

    @property
    def busy(self):
        """Se ainda há eventos ou animações pendentes."""
        return bool(self.queue) or self.wait > 0 or any(not f.done for f in self.flights)

    def enqueue(self, events):
        """Agenda eventos do motor para serem animados em ordem."""
        self.queue.extend(events)

    def update(self, dt):
        """Anima voos e efeitos e apresenta o próximo evento quando for a hora."""
        self.time += dt
        for f in self.flights:
            f.update(dt)
        self.flights = [f for f in self.flights if not f.done]
        self.floats = [f for f in self.floats if not f.update(dt)]
        self.particles.update(dt)
        for i in list(self.board_flip):
            if self.board_flip[i] < 1.0 and i < self.board_visible:
                self.board_flip[i] = min(1.0, self.board_flip[i] + dt * 4)
        self.wait -= dt
        while self.wait <= 0 and self.queue:
            self._present(self.queue.popleft())

    def _present(self, ev):
        """Começa a animação de um evento."""
        self.wait = EVENT_PAUSE.get(ev.kind, 0.3)
        if ev.text:
            self.log.append(ev.text)
            self.log = self.log[-40:]
        kind = ev.kind
        if kind == "blind":
            self._bet_flight(ev.seat, self.bets.get(ev.seat, 0) + ev.amount)
        elif kind == "action":
            self._present_action(ev)
        elif kind == "deal":
            self._deal_flights(ev)
        elif kind == "collect":
            self._collect_flights(ev.amount)
        elif kind == "board":
            self._board_flights(ev.cards)
        elif kind == "lucky":
            self.sound.play("powerup")
            self.floats.append(FloatText("Trevo da Sorte!", (TABLE_CENTER[0], BOARD_Y - 70), (110, 230, 140), 34))
            self.particles.burst((TABLE_CENTER[0], BOARD_Y), [(110, 230, 140), (255, 255, 255)], 30, 200)
        elif kind in ("reveal", "showdown"):
            self.reveal = True
            self.shown_hand_names = kind == "showdown"
            self.sound.play("card")
        elif kind == "shield":
            self.sound.play("powerup")
            self.floats.append(FloatText(f"Escudo +{ev.amount}", SEAT_POS[ev.seat], (200, 130, 255), 30))
            self.stacks[ev.seat] = self.stacks.get(ev.seat, 0) + ev.amount
        elif kind == "win":
            self._win(ev)
        elif kind == "discard_phase":
            self.floats.append(FloatText("Pineapple: descarte 1 carta", (TABLE_CENTER[0], BOARD_Y - 70), C.WARNING, 30))
        elif kind == "discard":
            self.sound.play("card")
            visible = self.hole_visible.get(ev.seat, 0)
            if visible:
                self.flights.append(Flight(hole_center(ev.seat, visible - 1, visible), DECK_POS, 0.35, kind="card"))
                self.hole_visible[ev.seat] = visible - 1
        elif kind == "swap":
            self.sound.play("card")
            old_pos = hole_center(ev.seat, 0, len(self.session.players[ev.seat].hole))
            self.flights.append(Flight(old_pos, DECK_POS, 0.35, kind="card"))
            self.flights.append(Flight(DECK_POS, old_pos, 0.4, 0.15, kind="card"))

    def _present_action(self, ev):
        """Animação de uma jogada: pagar, aumentar, passar ou desistir."""
        if ev.action == "call":
            self._bet_flight(ev.seat, self.bets.get(ev.seat, 0) + ev.amount)
        elif ev.action == "raise":
            self._bet_flight(ev.seat, ev.amount)
        elif ev.action == "check":
            self.sound.play("check")
        elif ev.action == "fold":
            self.sound.play("fold")
            visible = self.hole_visible.get(ev.seat, 0)
            for k in range(visible):
                self.flights.append(Flight(hole_center(ev.seat, k, visible), DECK_POS, 0.35, kind="card"))
            self.hole_visible[ev.seat] = 0

    def _bet_flight(self, seat, new_bet):
        """Fichas saem do jogador e param na frente dele (a aposta dele passa a ser ``new_bet``)."""
        self.sound.play("chip")
        paid = new_bet - self.bets.get(seat, 0)
        self.stacks[seat] = self.stacks.get(seat, 0) - paid

        def land():
            self.bets[seat] = new_bet

        self.flights.append(Flight(SEAT_POS[seat], BET_POS[seat], 0.3, kind="chips", payload=paid, on_land=land))

    def _deal_flights(self, ev):
        """Cartas voam do baralho até o jogador, uma de cada vez."""
        for k in range(len(ev.cards)):
            def land(seat=ev.seat):
                self.hole_visible[seat] = self.hole_visible.get(seat, 0) + 1
                self.sound.play("card")
            delay = k * 0.35
            target = hole_center(ev.seat, k, len(ev.cards))
            self.flights.append(Flight(DECK_POS, target, 0.32, delay, kind="card", on_land=land))

    def _collect_flights(self, total):
        """As apostas da rodada voam para o pote."""
        bets = [(seat, amount) for seat, amount in self.bets.items() if amount]
        self.bets = {}
        if not bets:
            self.pot = total
            return
        self.sound.play("chip")

        def land():
            self.pot = total

        for seat, amount in bets:
            self.flights.append(Flight(BET_POS[seat], POT_POS, 0.35, kind="chips", payload=amount, on_land=land))

    def _board_flights(self, cards):
        """Cartas comunitárias voam para a mesa e viram ao chegar."""
        start = self.board_visible
        for k, card in enumerate(cards):
            i = start + k

            def land(i=i):
                self.board_visible = max(self.board_visible, i + 1)
                self.board_flip[i] = 0.0
                self.sound.play("card")

            self.flights.append(Flight(DECK_POS, board_slot(i), 0.3, k * 0.16, kind="card", on_land=land))
        self.wait += 0.16 * len(cards) + 0.3

    def _win(self, ev):
        """O pote voa para o vencedor, com som, confete e a faixa de resultado."""
        p = self.session.players[ev.seat]
        hand = self.session.hand
        name = known_hand_name(hand, p.hole) if hand.street == "showdown" else ""
        self.winners[ev.seat] = name
        self.pot = max(0, self.pot - ev.amount)

        def land():
            self.stacks[ev.seat] = self.stacks.get(ev.seat, 0) + ev.amount
            self.floats.append(FloatText(f"+{draw.format_chips(ev.amount)}", SEAT_POS[ev.seat], C.GOLD, 34))

        self.flights.append(Flight(POT_POS, SEAT_POS[ev.seat], 0.5, kind="chips", payload=ev.amount, on_land=land))
        if p.is_human:
            self.sound.play("win")
            self.particles.burst(SEAT_POS[ev.seat], [C.GOLD, C.ACCENT, (255, 255, 255)], 50)
            self.banner = f"Você ganhou {draw.format_chips(ev.amount)}" + (f" com {name}!" if name else "!")
        else:
            self.sound.play("chip")
            if not self.banner:
                self.banner = f"{p.name} ganhou {draw.format_chips(ev.amount)}" + (f" com {name}" if name else "")

    def draw(self, surface, extras):
        """Desenha a mesa inteira.

        Args:
            extras: dicionário com informações dos power-ups e da interface:
                ``peek`` (carta espiada), ``equities`` (assento -> chance),
                ``target`` (``"own_card"``/``"opponent"`` durante a escolha),
                ``hover_seat`` e ``hover_card``.
        """
        hand = self.session.hand
        self._draw_felt(surface)
        self._draw_board(surface, hand, extras.get("peek"))
        if self.pot:
            draw.chip_stack(surface, (POT_POS[0] - 50, POT_POS[1] + 6), self.pot, 11)
            label = draw.text_surface(f"Pote: {draw.format_chips(self.pot)}", 28, C.TEXT, True)
            box = label.get_rect(midleft=(POT_POS[0] - 30, POT_POS[1])).inflate(20, 10)
            draw.alpha_rect(surface, box, (0, 0, 0), 110, 14)
            surface.blit(label, label.get_rect(center=box.center))
        for seat, amount in self.bets.items():
            if amount:
                x, y = BET_POS[seat]
                draw.chip_stack(surface, (x - 22, y), amount, 10)
                draw.text(surface, draw.format_chips(amount), (x - 6, y), 22, C.TEXT, True, "midleft")
        self._draw_dealer_button(surface)
        for p in self.session.players:
            if p is not None:
                self._draw_seat(surface, p, hand, extras)
        for f in self.flights:
            if not f.started:
                continue
            if f.kind == "chips":
                draw.chip_stack(surface, f.pos, f.payload or 1, 10, 4)
            else:
                draw.draw_card(surface, None, f.pos, *HOLE_CARD, face_up=False)
        self.particles.draw(surface)
        for f in self.floats:
            f.draw(surface)
        if self.banner and hand and hand.finished and not self.busy:
            surf = draw.text_surface(self.banner, 32, C.GOLD, True)
            box = surf.get_rect(center=(TABLE_CENTER[0], BOARD_Y + 78)).inflate(36, 16)
            draw.alpha_rect(surface, box, (0, 0, 0), 170, 12)
            surface.blit(surf, surf.get_rect(center=box.center))

    def _draw_felt(self, surface):
        """Borda de madeira e o feltro verde da mesa."""
        rim = FELT_RECT.inflate(36, 36)
        pygame.draw.ellipse(surface, (5, 10, 15), rim.move(0, 8))
        pygame.draw.ellipse(surface, C.RIM, rim)
        pygame.draw.ellipse(surface, C.RIM_LIGHT, rim, 4)
        pygame.draw.ellipse(surface, C.FELT, FELT_RECT)
        pygame.draw.ellipse(surface, C.FELT_DARK, FELT_RECT.inflate(-60, -60), 3)
        draw.text(surface, "POKER POWER-UP", (TABLE_CENTER[0], TABLE_CENTER[1] + 110), 30, (34, 128, 86), True, "center")

    def _draw_board(self, surface, hand, peek):
        """As 5 cartas comunitárias (virando ao chegar) e a carta espiada, se houver."""
        w, h = BOARD_CARD
        for i in range(5):
            center = board_slot(i)
            if hand and i < self.board_visible and i < len(hand.board):
                flip = self.board_flip.get(i, 1.0)
                highlight = C.GOLD if self._card_wins(hand.board[i]) else None
                if flip < 0.5:
                    draw.draw_card(surface, None, center, w, h, False, max(0.05, 1 - flip * 2))
                else:
                    draw.draw_card(surface, hand.board[i], center, w, h, True, max(0.05, flip * 2 - 1), highlight=highlight)
            else:
                draw.card_slot(surface, center, w, h)
        if peek and hand and peek[1] >= self.board_visible:
            center = board_slot(peek[1])
            draw.draw_card(surface, peek[0], center, w, h, True, alpha=150)
            draw.text(surface, "PRÓXIMA", (center[0], center[1] + h // 2 + 12), 20, C.INFO, True, "center")

    def _card_wins(self, card):
        """Se a carta da mesa faz parte da mão de um vencedor no showdown (para destacá-la)."""
        if not self.shown_hand_names or self.busy:
            return False
        return any(card in self._best_five(self.session.players[seat].hole) for seat in self.winners)

    def _best_five(self, hole):
        """As 5 cartas que formam a melhor mão de ``hole`` (para destacar, com cache)."""
        hand = self.session.hand
        if any(card is None for card in hole):
            return ()
        key = (tuple(hole), tuple(hand.board), hand.variant.key)
        if key not in self._best_cache:
            self._best_cache[key] = hand.variant.best_cards(hole, hand.board)
        return self._best_cache[key]

    def _draw_dealer_button(self, surface):
        """Botão "D" do dealer, entre o assento e a aposta dele."""
        seat = self.session.button_seat
        x, y = SEAT_POS[seat]
        bx, by = BET_POS[seat]
        pos = (int(x + (bx - x) * 0.45 + 70), int(y + (by - y) * 0.45))
        pygame.draw.circle(surface, (0, 0, 0), (pos[0] + 1, pos[1] + 2), 13)
        pygame.draw.circle(surface, (245, 245, 245), pos, 13)
        draw.text(surface, "D", pos, 22, (20, 20, 20), True, "center")

    def _draw_seat(self, surface, p, hand, extras):
        """Cartas, painel (nome e fichas) e etiqueta de um jogador."""
        seat = p.seat
        x, y = SEAT_POS[seat]
        in_this_hand = hand is not None and p in hand.players
        out = p.stack == 0 and not in_this_hand
        if self.session.mode == "tournament" and out:
            rect = pygame.Rect(0, 0, *SEAT_SIZE)
            rect.center = (x, y)
            draw.panel(surface, rect, C.BG_DARK, C.PANEL, 12)
            draw.text(surface, f"{p.name} - eliminado", rect.center, 20, C.TEXT_FAINT, False, "center")
            return

        visible = self.hole_visible.get(seat, 0) if in_this_hand else 0
        shown = min(visible, len(p.hole))
        for k in range(shown):
            center = hole_center(seat, k, shown)
            if p.is_human:
                choosing = extras.get("target") == "own_card" or extras.get("discard")
                winning = self.shown_hand_names and seat in self.winners and p.hole[k] in self._best_five(p.hole)
                highlight = None
                if choosing and extras.get("hover_card") == k:
                    highlight = C.ACCENT
                elif winning:
                    highlight = C.GOLD
                draw.draw_card(surface, p.hole[k], center, *HUMAN_CARD, True, highlight=highlight)
            else:
                face = (self.reveal and p.show_cards) or k in p.revealed
                tilt = (k - (shown - 1) / 2) * (16 / max(2, shown))
                surf = draw.card_surface(p.hole[k], *HOLE_CARD, face)
                surf = pygame.transform.rotozoom(surf, -tilt, 1.0)
                surface.blit(surf, surf.get_rect(center=center))
                if k in p.revealed and not (self.reveal and p.show_cards):
                    pygame.draw.rect(surface, (200, 130, 255), surf.get_rect(center=center), 2, border_radius=6)

        rect = pygame.Rect(0, 0, *SEAT_SIZE)
        rect.center = (x, y)
        acting = hand is not None and not hand.finished and hand.current_player is p and not self.busy
        border = C.PANEL_BORDER
        if acting:
            pulse = 0.5 + 0.5 * math.sin(self.time * 6)
            border = draw.lerp_color(C.ACCENT_DARK, C.ACCENT, pulse)
        if seat in self.winners and not self.busy:
            border = C.GOLD
        hover_target = extras.get("target") == "opponent" and extras.get("hover_seat") == seat and not p.is_human
        if hover_target:
            border = (200, 130, 255)
        bg = C.PANEL if not (in_this_hand and p.folded) else (20, 30, 38)
        draw.panel(surface, rect, bg, border, 12, 3 if (acting or hover_target or seat in self.winners) else 2)
        pygame.draw.circle(surface, p.color, (rect.left + 28, rect.centery), 19)
        draw.text(surface, p.name[0].upper(), (rect.left + 28, rect.centery), 26, C.BG, True, "center")
        name_color = C.TEXT if not (in_this_hand and p.folded) else C.TEXT_FAINT
        draw.text(surface, p.name, (rect.left + 54, rect.top + 8), 23, name_color, True)
        draw.text(surface, draw.format_chips(self.stacks.get(seat, p.stack)), (rect.left + 54, rect.top + 31), 23, C.GOLD)

        label, color = "", C.TEXT_DIM
        if in_this_hand:
            if self.shown_hand_names and p.in_hand and hand:
                label, color = known_hand_name(hand, p.hole), (C.GOLD if seat in self.winners else C.TEXT)
            elif p.last_action and not acting:
                label = ACTION_LABELS.get(p.last_action, p.last_action)
                color = C.DANGER if p.last_action == "All-in" else C.TEXT_DIM
            elif acting and not p.is_human:
                label = "pensando" + "." * (int(self.time * 3) % 4)
        if label:
            tag = draw.text_surface(label, 20, color, True)
            box = tag.get_rect(midtop=(x, rect.bottom + 4)).inflate(14, 6)
            draw.alpha_rect(surface, box, (0, 0, 0), 150, 9)
            surface.blit(tag, tag.get_rect(center=box.center))

        equities = extras.get("equities")
        if equities and seat in equities and p.in_hand:
            badge = pygame.Rect(0, 0, 70, 28)
            badge.midbottom = (rect.right - 10, rect.top - 2) if not p.is_human else (rect.right + 40, rect.centery)
            draw.panel(surface, badge, (60, 45, 10), C.GOLD, 10)
            draw.text(surface, f"{equities[seat]:.0%}", badge.center, 24, C.GOLD, True, "center")

    @staticmethod
    def seat_rect(seat):
        """Retângulo do painel de um assento (para clicar em adversários)."""
        rect = pygame.Rect(0, 0, *SEAT_SIZE)
        rect.center = SEAT_POS[seat]
        return rect.inflate(0, 90).move(0, -30)

    @staticmethod
    def human_card_rect(k, n=2):
        """Retângulo da k-ésima de ``n`` cartas do jogador (Troca e descarte).

        Com muitas cartas elas se sobrepõem; o retângulo é cortado para a
        parte visível, assim o clique acerta a carta que está por cima.
        """
        rect = pygame.Rect(0, 0, *HUMAN_CARD)
        rect.center = hole_center(0, k, n)
        if k < n - 1:
            rect.width = min(rect.width, HUMAN_SPACING.get(n, 38))
        return rect
