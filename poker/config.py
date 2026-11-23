"""Constantes da interface: tamanho da janela, cores e caminhos."""

from pathlib import Path

TITLE = "Poker Power-Up"
WIDTH = 1280
HEIGHT = 720
FPS = 60

ROOT = Path(__file__).resolve().parent.parent
SAVE_FILE = ROOT / "data" / "save.json"

STARTING_BANKROLL = 2000
REFILL_AMOUNT = 1000
REFILL_BELOW = 40

BG = (15, 25, 35)
BG_DARK = (10, 18, 26)
PANEL = (26, 40, 52)
PANEL_LIGHT = (36, 54, 68)
PANEL_BORDER = (52, 74, 90)
TEXT = (235, 241, 245)
TEXT_DIM = (150, 168, 180)
TEXT_FAINT = (95, 115, 130)
ACCENT = (31, 214, 95)
ACCENT_DARK = (22, 160, 70)
DANGER = (231, 76, 60)
WARNING = (241, 180, 40)
INFO = (60, 160, 240)
GOLD = (255, 200, 60)

FELT = (22, 110, 70)
FELT_DARK = (16, 82, 52)
RIM = (54, 38, 28)
RIM_LIGHT = (92, 66, 46)

CARD_FACE = (248, 248, 244)
CARD_RED = (210, 40, 50)
CARD_BLACK = (25, 28, 34)
CARD_BACK = (40, 70, 160)
CARD_BACK_LINE = (80, 115, 210)

DIFFICULTY_LABELS = {"easy": "Fácil", "medium": "Médio", "hard": "Difícil"}
DIFFICULTY_COLORS = {"easy": ACCENT, "medium": WARNING, "hard": DANGER}
