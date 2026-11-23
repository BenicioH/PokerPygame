"""Jogo salvo: saldo, nome, preferências e power-ups guardados.

Os dados ficam em ``data/save.json``. O arquivo é lido com cuidado: valores
faltando ou estragados são trocados pelos valores padrão, para que um save
corrompido nunca impeça o jogo de abrir.
"""

import json

from .config import SAVE_FILE, STARTING_BANKROLL
from .engine import powerups

DEFAULTS = {
    "name": "Você",
    "bankroll": STARTING_BANKROLL,
    "music": True,
    "sfx": True,
    "inventory": [],
    "hands_played": 0,
    "tournaments_won": 0,
    "best_cashout": 0,
}


class SaveData:
    """Dados persistentes do jogador."""

    def __init__(self, path=SAVE_FILE):
        self.path = path
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        """Lê o arquivo, se existir, mantendo só valores do tipo esperado."""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        for key, default in DEFAULTS.items():
            value = raw.get(key)
            if type(value) is type(default):
                self.data[key] = value
        self.data["bankroll"] = max(0, self.data["bankroll"])
        self.data["inventory"] = [k for k in self.data["inventory"]
                                  if isinstance(k, str) and k in powerups.BY_KEY][:powerups.MAX_INVENTORY]
        self.data["name"] = self.data["name"].strip()[:14] or DEFAULTS["name"]

    def save(self):
        """Grava no disco (cria a pasta ``data`` se precisar)."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        """Muda um valor e já grava no disco."""
        self.data[key] = value
        self.save()

    def inventory_objects(self):
        """Power-ups salvos como objetos."""
        return [powerups.create(key) for key in self.data["inventory"]]

    def store_inventory(self, items):
        """Salva a lista de power-ups do jogador."""
        self["inventory"] = [p.key for p in items]
