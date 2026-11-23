"""Lobby: salas de Low, Medium e High Stakes com mesas de cash e torneios."""

import pygame

from .. import config as C
from ..engine.session import STAKES, CashSession, TournamentSession
from ..ui import draw
from ..ui.widgets import Button, Slider
from .base import Backdrop, ConfirmDialog, Modal, Scene

ROOM_METALS = {"low": "Bronze", "medium": "Prata", "high": "Ouro"}
ROOM_COLORS = {"low": (205, 127, 50), "medium": (192, 200, 210), "high": C.GOLD}
DIFFICULTIES = ["easy", "medium", "hard"]
DIFF_NUMERAL = {"easy": "I", "medium": "II", "hard": "III"}
TABS = [("cash", "Cash Game"), ("tournament", "Torneios")]


class LobbyScene(Scene):
    """Escolha de sala, modo e mesa."""

    def __init__(self, app, tab="cash", room="low"):
        super().__init__(app)
        self.backdrop = Backdrop(seed=9)
        self.tab = tab
        self.room = room
        self.appear = 0.0
        self._build()

    def _build(self):
        """Recria os botões para a aba e a sala atuais."""
        self.appear = 0.0
        self.buttons = [Button((30, 24, 130, 44), "< Menu", self._menu, "ghost", 24, pygame.K_ESCAPE)]
        for i, (key, label) in enumerate(TABS):
            style = "primary" if key == self.tab else "secondary"
            self.buttons.append(Button((260 + i * 230, 100, 215, 48), label, lambda k=key: self._set_tab(k), style, 26))
        if self.app.save["bankroll"] < C.REFILL_BELOW:
            self.buttons.append(Button((C.WIDTH - 250, 70, 220, 40), "Recarregar +1.000", self._refill, "warning", 22))
        for i, stake in enumerate(STAKES):
            style = "info" if stake == self.room else "secondary"
            self.buttons.append(Button((30, 200 + i * 76, 200, 62), STAKES[stake]["label"],
                                       lambda s=stake: self._set_room(s), style, 24,
                                       sublabel=f"Blinds {STAKES[stake]['sb']}/{STAKES[stake]['bb']}"))
        label = "Sentar" if self.tab == "cash" else "Inscrever"
        for i, diff in enumerate(DIFFICULTIES):
            self.buttons.append(Button((C.WIDTH - 210, 234 + i * 130, 170, 52), label,
                                       lambda d=diff: self._join(d), "primary", 26))

    def _menu(self):
        """Volta ao menu."""
        from .menu import MenuScene
        self.app.replace(MenuScene(self.app))

    def _set_tab(self, tab):
        """Troca de aba (cash ou torneios)."""
        self.tab = tab
        self._build()

    def _set_room(self, room):
        """Troca de sala (Low, Medium ou High Stakes)."""
        self.room = room
        self._build()

    def _refill(self):
        """Recarga grátis para quem ficou sem saldo."""
        self.app.save["bankroll"] += C.REFILL_AMOUNT
        self.app.toasts.push("+1.000 fichas grátis!", C.GOLD)
        self.app.sound.play("reward")
        self._build()

    def _join(self, difficulty):
        """Botão "Sentar"/"Inscrever": confere o saldo e abre a compra ou a confirmação."""
        info = STAKES[self.room]
        bankroll = self.app.save["bankroll"]
        if self.tab == "cash":
            if bankroll < info["min_buy"]:
                self._no_money(info["min_buy"])
                return
            self.app.push(BuyInDialog(self.app, self.room, difficulty))
        else:
            if bankroll < info["buyin"]:
                self._no_money(info["buyin"])
                return
            prize = info["buyin"] * 6
            message = (f"Buy-in de {draw.format_chips(info['buyin'])} fichas. Prêmio: "
                       f"1º lugar {draw.format_chips(int(prize * 0.65))}, 2º lugar {draw.format_chips(int(prize * 0.35))}.")
            self.app.push(ConfirmDialog(self.app, "Entrar no torneio?", message,
                                        lambda: self._start_tournament(difficulty), "Inscrever", danger=False))

    def _no_money(self, need):
        """Aviso de saldo insuficiente."""
        self.app.sound.play("error")
        self.app.toasts.push(f"Saldo insuficiente: precisa de {draw.format_chips(need)} fichas.", C.DANGER)

    def _start_tournament(self, difficulty):
        """Paga o buy-in e abre a mesa do torneio."""
        from .table import TableScene
        save = self.app.save
        save["bankroll"] -= STAKES[self.room]["buyin"]
        session = TournamentSession(save["name"], difficulty, self.room, inventory=save.inventory_objects())
        self.app.replace(TableScene(self.app, session))

    def update(self, dt):
        """Anima o fundo e a entrada das mesas."""
        self.appear = min(1.0, self.appear + dt * 4)
        self.backdrop.update(dt)
        super().update(dt)

    def draw(self, surface):
        """Título, saldo e o conteúdo da aba atual."""
        self.backdrop.draw(surface)
        draw.text(surface, "Lobby", (C.WIDTH // 2, 46), 48, C.TEXT, True, "center")
        draw.text(surface, f"Saldo: {draw.format_chips(self.app.save['bankroll'])}", (C.WIDTH - 30, 32), 30, C.GOLD, True, "topright")
        draw.text(surface, "Salas", (30, 172), 22, C.TEXT_DIM, True)
        for i, diff in enumerate(DIFFICULTIES):
            self._draw_table_row(surface, i, diff)
        super().draw(surface)

    def _draw_table_row(self, surface, i, diff):
        """Cartão de uma mesa: nome, dificuldade dos bots, blinds e buy-in (ou prêmio)."""
        info = STAKES[self.room]
        t = max(0.0, min(1.0, self.appear * 3 - i * 0.4))
        rect = pygame.Rect(260, 200 + i * 130, C.WIDTH - 290, 118)
        rect.x += int((1 - t) * 40)
        draw.panel(surface, rect, C.PANEL, C.PANEL_BORDER, 14)
        metal = ROOM_METALS[self.room]
        pygame.draw.circle(surface, ROOM_COLORS[self.room], (rect.left + 46, rect.centery), 26)
        draw.suit_shape(surface, i, (rect.left + 46, rect.centery), 26, C.BG)
        kind = "Mesa" if self.tab == "cash" else "Sit & Go"
        name = f"{kind} {metal} {DIFF_NUMERAL[diff]}"
        draw.text(surface, name, (rect.left + 90, rect.top + 18), 32, C.TEXT, True)
        badge = pygame.Rect(rect.left + 90, rect.top + 56, 130, 30)
        draw.panel(surface, badge, C.BG_DARK, C.DIFFICULTY_COLORS[diff], 15)
        draw.text(surface, f"Bots {C.DIFFICULTY_LABELS[diff]}", badge.center, 22, C.DIFFICULTY_COLORS[diff], True, "center")
        col = rect.left + 330
        if self.tab == "cash":
            lines = [("Blinds", f"{info['sb']}/{info['bb']}"),
                     ("Buy-in", f"{draw.format_chips(info['min_buy'])} - {draw.format_chips(info['max_buy'])}"),
                     ("Jogadores", "5/6")]
        else:
            prize = info["buyin"] * 6
            lines = [("Buy-in", draw.format_chips(info["buyin"])),
                     ("Prêmio total", draw.format_chips(prize)),
                     ("Fichas iniciais", draw.format_chips(TournamentSession.START_STACK))]
        for k, (label, value) in enumerate(lines):
            x = col + k * 170
            draw.text(surface, label, (x, rect.top + 26), 21, C.TEXT_DIM)
            draw.text(surface, value, (x, rect.top + 52), 30, C.TEXT, True)


class BuyInDialog(Modal):
    """Janela para escolher quantas fichas levar para a mesa de cash."""

    def __init__(self, app, stake, difficulty):
        super().__init__(app, 560, 330, "Comprar fichas")
        self.stake = stake
        self.difficulty = difficulty
        info = STAKES[stake]
        top = min(info["max_buy"], app.save["bankroll"])
        default = min(top, info["bb"] * 100)
        r = self.rect
        self.slider = Slider((r.left + 60, r.top + 170, r.width - 120, 12), info["min_buy"], top, default, info["bb"])
        self.buttons = [
            Button((r.left + 40, r.bottom - 80, 200, 52), "Cancelar", self.close, "secondary"),
            Button((r.right - 240, r.bottom - 80, 200, 52), "Sentar", self._confirm, "primary", hotkey=pygame.K_RETURN),
        ]

    def handle_event(self, event):
        """O controle deslizante vem antes dos botões."""
        if self.slider.handle_event(event):
            return True
        return super().handle_event(event)

    def _confirm(self):
        """Tira as fichas do saldo e abre a mesa de cash."""
        from .table import TableScene
        save = self.app.save
        amount = self.slider.value
        save["bankroll"] -= amount
        session = CashSession(save["name"], amount, self.difficulty, self.stake, inventory=save.inventory_objects())
        self.app.replace(TableScene(self.app, session))

    def draw_body(self, surface, rect):
        """Valor escolhido, controle deslizante e saldo que sobra."""
        info = STAKES[self.stake]
        draw.text(surface, f"{info['label']}  •  Blinds {info['sb']}/{info['bb']}  •  Bots {C.DIFFICULTY_LABELS[self.difficulty]}",
                  (rect.centerx, rect.top + 76), 23, C.TEXT_DIM, False, "center")
        draw.text(surface, draw.format_chips(self.slider.value), (rect.centerx, rect.top + 124), 46, C.GOLD, True, "center")
        self.slider.rect.topleft = (rect.left + 60, rect.top + 170)
        self.slider.draw(surface)
        bb = self.slider.value // info["bb"]
        draw.text(surface, f"{bb} big blinds  •  Saldo após: {draw.format_chips(self.app.save['bankroll'] - self.slider.value)}",
                  (rect.centerx, rect.top + 205), 21, C.TEXT_DIM, False, "center")
