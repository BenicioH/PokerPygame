"""Teste automático da interface sem janela.

Abre o jogo com o driver de vídeo "dummy", passa por todas as telas, joga
mãos com um bot no lugar do jogador, usa todos os power-ups, gira a roleta
e salva capturas de tela em ``shots/``. Serve para achar erros que só
aparecem com a interface rodando.

Uso: python tools/autoplay.py [mãos]
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from poker import config  # noqa: E402

TEMP_SAVE = Path(tempfile.mkdtemp()) / "save.json"
config.SAVE_FILE = TEMP_SAVE

from poker.app import App  # noqa: E402
from poker.engine import minigames as mg  # noqa: E402
from poker.engine import powerups  # noqa: E402
from poker.engine.bots import make_bot  # noqa: E402
from poker.scenes.base import ConfirmDialog  # noqa: E402
from poker.scenes.lobby import BuyInDialog, LobbyScene  # noqa: E402
from poker.scenes.menu import MenuScene  # noqa: E402
from poker.scenes.minigame import MiniGameScene  # noqa: E402
from poker.scenes.roulette import RouletteScene  # noqa: E402
from poker.scenes.settings import SettingsScene  # noqa: E402
from poker.scenes.table import TableScene  # noqa: E402
from poker.scenes.tutorial import TutorialScene  # noqa: E402

OUT = ROOT / "shots"
OUT.mkdir(exist_ok=True)
DT = 1 / 60


def frames(app, seconds):
    """Roda o jogo por ``seconds`` segundos de tempo simulado."""
    for _ in range(int(seconds / DT)):
        app.top.update(DT)
        app.toasts.update(DT)
        app._draw()


def shot(app, name):
    """Desenha a tela e salva em ``shots/<name>.png``."""
    app._draw()
    pygame.image.save(app.screen, str(OUT / f"{name}.png"))
    print("shot", name)


def click(app, pos):
    """Clique com o botão esquerdo em ``pos``."""
    for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        app.top.handle_event(pygame.event.Event(kind, pos=pos, button=1))


def key(app, k):
    """Aperta a tecla ``k``."""
    app.top.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def press(scene, k):
    """Aperta a tecla ``k`` direto na tela do mini game."""
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def play_minigame(app, scene, prefix, taken):
    """Joga um mini game apertando teclas como uma pessoa faria."""
    game = scene.control.key
    step = 0
    while app.top is scene:
        step += 1
        if scene.phase == "play":
            if game == "climb" and step % 7 == 0:
                press(scene, pygame.K_SPACE)
            elif game == "race" and step % 7 == 0:
                runner = scene.runner
                if any(0 < h - runner.pos <= 1 for h in mg.HURDLES):
                    press(scene, pygame.K_UP)
                press(scene, pygame.K_LEFT if runner.last != "left" else pygame.K_RIGHT)
            elif game == "quiz" and step % 90 == 0:
                press(scene, pygame.K_1 + (step // 90) % 4)
            if f"{game}_play" not in taken and scene.timer > 3.0:
                taken.add(f"{game}_play")
                shot(app, f"{prefix}_mg_{game}_play")
            if game == "quiz" and "quiz_reveal" not in taken and scene.control.state()["phase"] == "reveal":
                taken.add("quiz_reveal")
                shot(app, f"{prefix}_mg_quiz_reveal")
        elif scene.phase == "intro" and f"{game}_intro" not in taken and scene.timer > 1.0:
            taken.add(f"{game}_intro")
            shot(app, f"{prefix}_mg_{game}_intro")
        elif scene.phase == "results" and f"{game}_results" not in taken and scene.timer > 1.0:
            taken.add(f"{game}_results")
            shot(app, f"{prefix}_mg_{game}_results")
        elif scene.phase == "choose":
            if "choose" not in taken:
                taken.add("choose")
                shot(app, f"{prefix}_mg_choose")
            scene.buttons[1].click()
        elif scene.phase == "announce" and "announce" not in taken:
            taken.add("announce")
            shot(app, f"{prefix}_mg_announce")
        frames(app, DT)


def close_overlays(app, prefix):
    """Termina a roleta, o mini game ou a recompra que ficaram abertos por cima da mesa."""
    while True:
        top = app.top
        if isinstance(top, RouletteScene):
            top._spin()
            frames(app, 5.0)
            top._close()
        elif isinstance(top, MiniGameScene):
            play_minigame(app, top, prefix, set())
        elif isinstance(top, ConfirmDialog):
            top._yes()
        else:
            return


def play_table(app, table, hands, prefix, use_powerups=False):
    """Joga ``hands`` mãos com um bot decidindo pelo jogador."""
    brain = make_bot("medium")
    played = 0
    shots_taken = set()
    guard = 0
    while played < hands and app.top is not None:
        guard += 1
        if guard > 60 * 60 * 30:
            raise RuntimeError("travou")
        top = app.top
        if isinstance(top, MiniGameScene):
            play_minigame(app, top, prefix, shots_taken)
            continue
        if isinstance(top, RouletteScene):
            first = "roulette" not in shots_taken
            shots_taken.add("roulette")
            if first:
                shot(app, f"{prefix}_roulette")
            top._remove(top.roulette.active[0].key)
            if first:
                shot(app, f"{prefix}_roulette_removed")
            top._spin()
            frames(app, 2.0)
            if first:
                shot(app, f"{prefix}_roulette_spinning")
            frames(app, 3.0)
            if first:
                shot(app, f"{prefix}_roulette_result")
            top._close()
            continue
        if isinstance(top, ConfirmDialog):
            top._yes()
            continue
        if top is not table:
            print("top scene changed:", type(top).__name__)
            return played
        s = table.session
        hand = s.hand
        if hand is None:
            frames(app, 0.1)
            continue
        if use_powerups and s.inventory and not table.view.busy and s.human.in_hand and not hand.finished:
            for i, pu in enumerate(list(s.inventory)):
                if pu.can_use(hand, s.human)[0]:
                    table._click_slot(i)
                    if table.targeting:
                        if pu.target == "own_card":
                            click(app, table.view.human_card_rect(0).center)
                        else:
                            opp = next(p for p in hand.players if p is not s.human and p.in_hand)
                            click(app, table.view.seat_rect(opp.seat).center)
                    frames(app, 0.6)
                    shot(app, f"{prefix}_pu_{pu.key}")
                    break
        if table._must_discard():
            if "discard" not in shots_taken:
                shots_taken.add("discard")
                shot(app, f"{prefix}_discard")
            table._discard(0)
        if hand.variant.key != "holdem" and f"variant_{hand.variant.key}" not in shots_taken \
                and len(hand.board) >= 3 and not table.view.busy:
            shots_taken.add(f"variant_{hand.variant.key}")
            shot(app, f"{prefix}_variant_{hand.variant.key}")
        if table._human_turn():
            if "turn" not in shots_taken and len(hand.board) >= 3:
                shots_taken.add("turn")
                table._quick_bet(0.5)
                table._refresh_buttons()
                shot(app, f"{prefix}_human_turn")
            kind, amount = brain.decide(hand, s.human)
            if kind == "raise":
                table.slider.set_value(amount)
                table._raise()
            else:
                table._act(kind)
        if hand.finished and not table.view.busy:
            if hand.street == "showdown" and "showdown" not in shots_taken:
                frames(app, 0.3)
                shots_taken.add("showdown")
                shot(app, f"{prefix}_showdown")
            frames(app, 0.2)
            table._next_hand()
            played += 1
            continue
        frames(app, DT * 6)
    return played


def main():
    """Passa por todas as telas e joga um cash game e um torneio inteiro."""
    hands = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    app = App()
    app.save.data["bankroll"] = 20000
    app.replace(MenuScene(app))
    frames(app, 0.5)
    shot(app, "01_menu")

    app.replace(TutorialScene(app))
    for page in range(5):
        frames(app, 0.2)
        shot(app, f"02_tutorial_{page + 1}")
        app.top._go(1)
    app.replace(SettingsScene(app))
    frames(app, 0.3)
    shot(app, "03_settings")

    lobby = LobbyScene(app)
    app.replace(lobby)
    frames(app, 0.6)
    shot(app, "04_lobby_cash")
    lobby._set_room("high")
    frames(app, 0.6)
    lobby._set_tab("tournament")
    frames(app, 0.6)
    shot(app, "05_lobby_tournament")
    lobby._set_tab("cash")
    lobby._set_room("medium")
    lobby._join("hard")
    frames(app, 0.4)
    assert isinstance(app.top, BuyInDialog)
    shot(app, "07_buyin")
    app.top._confirm()
    table = app.top
    assert isinstance(table, TableScene)
    table.session.inventory = [cls() for cls in powerups.ALL_POWERUPS[:4]]
    frames(app, 1.2)
    shot(app, "08_table_deal")
    played = play_table(app, table, hands, "09_cash", use_powerups=True)
    print("cash hands played:", played)
    close_overlays(app, "09_cash")
    if app.top is table:
        table.session.inventory = [cls() for cls in powerups.ALL_POWERUPS[4:]]
        play_table(app, table, 4, "10_cash2", use_powerups=True)
        close_overlays(app, "10_cash2")
        key(app, pygame.K_ESCAPE)
        frames(app, 0.3)
        shot(app, "11_pause")
        app.pop()
        table._leave()
    frames(app, 1.2)
    shot(app, "12_results_cash")

    lobby = LobbyScene(app, tab="tournament")
    app.replace(lobby)
    lobby._start_tournament("easy")
    table = app.top
    table.session.inventory = []
    played = play_table(app, table, 400, "13_tourney")
    print("tournament hands:", played, "top:", type(app.top).__name__)
    frames(app, 1.0)
    shot(app, "14_results_tournament")
    print("bankroll", app.save["bankroll"], "save at", TEMP_SAVE)


if __name__ == "__main__":
    main()
