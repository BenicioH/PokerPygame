"""Sessões de jogo: cash game e torneio.

Uma sessão junta várias mãos seguidas na mesma mesa. Ela cuida do que fica
entre uma mão e outra: mover o botão do dealer, repor bots quebrados (cash),
subir os blinds e eliminar jogadores (torneio), contar as mãos até o próximo
giro da roleta e guardar os power-ups do jogador.
"""

import random

from .bots import make_bot
from .hand import Hand
from .minigames import GAME_KEYS
from .player import Player
from .powerups import MAX_INVENTORY, SPIN_EVERY, Roulette, UseResult
from .variants import best_discard
from .variants import get as get_variant

SEATS = 6
MINIGAME_EVERY = 2

STAKES = {
    "low": {"label": "Low Stakes", "sb": 1, "bb": 2, "min_buy": 40, "max_buy": 200, "buyin": 50},
    "medium": {"label": "Medium Stakes", "sb": 5, "bb": 10, "min_buy": 200, "max_buy": 1000, "buyin": 250},
    "high": {"label": "High Stakes", "sb": 25, "bb": 50, "min_buy": 1000, "max_buy": 5000, "buyin": 1000},
}

BOT_NAMES = [
    "Lucas", "Marina", "Rafa", "Bia", "Duda", "Caio", "Nina", "Theo",
    "Lia", "Gui", "Malu", "Davi", "Iara", "Enzo", "Clara", "Otávio",
]
BOT_COLORS = [
    (231, 76, 60), (52, 152, 219), (155, 89, 182), (241, 196, 15),
    (26, 188, 156), (230, 126, 34), (236, 112, 160), (149, 165, 166),
]
HUMAN_COLOR = (46, 204, 113)


def _pay_removal(player, roulette, key):
    """Tira ``key`` da roleta pagando com as fichas de ``player`` (se der)."""
    if not roulette.can_remove(key, player.stack):
        return False
    player.stack -= roulette.remove(key)
    return True


class Session:
    """Base comum ao cash game e ao torneio.

    Args:
        human_name: nome do jogador.
        stack: fichas com que o jogador senta.
        difficulty: ``"easy"``, ``"medium"`` ou ``"hard"`` (bots).
        stake: chave de :data:`STAKES`.
    """

    mode = "base"

    def __init__(self, human_name, stack, difficulty, stake, rng=None, inventory=None):
        self._setup_table(difficulty, stake, rng)
        self.human = Player(human_name, stack, is_human=True, color=HUMAN_COLOR)
        self.human.seat = 0
        self.players[0] = self.human
        self.hands_until_spin = SPIN_EVERY
        self.inventory = list(inventory or [])
        self.active_effects = []
        self.stats = {"hands": 0, "won": 0, "biggest_pot": 0, "powerups_used": 0, "start": stack,
                      "rebought": 0}

    def _setup_table(self, difficulty, stake, rng):
        """Mesa vazia: assentos, botão, contadores, Hold'em e ordem dos mini games."""
        self.rng = rng or random.Random()
        self.difficulty = difficulty
        self.stake = stake
        self.players = [None] * SEATS
        self._used_names = set()
        self.button_seat = self.rng.randrange(SEATS)
        self.hand = None
        self.hands_played = 0
        self.variant = get_variant("holdem")
        self.minigame_order = self.rng.sample(GAME_KEYS, len(GAME_KEYS))
        self.minigames_played = 0
        self.hands_until_minigame = MINIGAME_EVERY

    def minigame_due(self):
        """Mini game a cada ``MINIGAME_EVERY`` mãos (com pelo menos 2 jogadores)."""
        return self.hands_until_minigame <= 0 and len(self.seated()) >= 2

    def next_minigame(self):
        """Escolhe o próximo mini game (os três se revezam) e reinicia a contagem."""
        key = self.minigame_order[self.minigames_played % len(self.minigame_order)]
        self.minigames_played += 1
        self.hands_until_minigame = MINIGAME_EVERY
        return key

    def minigame_players(self):
        """Quem disputa o mini game: ``(assento, nome, é_bot, dificuldade, cor)``."""
        return [(p.seat, p.name, p.bot is not None, self.difficulty, p.color) for p in self.seated()]

    def set_variant(self, key):
        """Muda a modalidade das próximas mãos (escolha de quem venceu o mini game)."""
        self.variant = get_variant(key)

    def bot_discards(self):
        """Pineapple: os bots que precisam descartar descartam agora."""
        events = []
        hand = self.hand
        for p in list(hand.awaiting_discard or []):
            if p.bot is not None:
                events += hand.discard(p, best_discard(p.hole))
        return events

    def _new_bot(self, seat, stack):
        """Senta um bot novo em ``seat`` (no lugar do bot que estava lá, se houver)."""
        if self.players[seat] is not None:
            self._used_names.discard(self.players[seat].name)
        free = [n for n in BOT_NAMES if n not in self._used_names] or BOT_NAMES
        name = self.rng.choice(free)
        self._used_names.add(name)
        bot = Player(name, stack, bot=make_bot(self.difficulty, self.rng),
                     color=self.rng.choice(BOT_COLORS))
        bot.seat = seat
        self.players[seat] = bot

    def blinds(self):
        """Valores atuais ``(small_blind, big_blind)``."""
        info = STAKES[self.stake]
        return info["sb"], info["bb"]

    def seated(self):
        """Jogadores sentados com fichas, na ordem dos assentos."""
        return [p for p in self.players if p is not None and p.stack > 0]

    def before_hand(self):
        """Ajustes entre mãos (as subclasses completam)."""

    def new_hand(self):
        """Começa uma mão nova e devolve os eventos iniciais."""
        self.before_hand()
        self.active_effects = []
        active = self.seated()
        for k in range(1, SEATS + 1):
            seat = (self.button_seat + k) % SEATS
            p = self.players[seat]
            if p is not None and p.stack > 0:
                self.button_seat = seat
                break
        button_index = next(i for i, p in enumerate(active) if p.seat == self.button_seat)
        sb, bb = self.blinds()
        self.hand = Hand(active, button_index, sb, bb, self.rng, self.variant)
        return self.hand.start()

    def end_hand(self):
        """Atualiza contadores e estatísticas quando a mão termina."""
        hand = self.hand
        self.hands_played += 1
        self.stats["hands"] += 1
        self.stats["biggest_pot"] = max(self.stats["biggest_pot"], hand.pot)
        if any(p is self.human for p, _, _ in hand.winners):
            self.stats["won"] += 1
        if len(self.inventory) < MAX_INVENTORY:
            self.hands_until_spin -= 1
        self.hands_until_minigame -= 1

    def spin_due(self):
        """Se é hora de girar a roleta (a cada 3 mãos, com espaço no inventário)."""
        return self.hands_until_spin <= 0 and len(self.inventory) < MAX_INVENTORY

    def make_roulette(self):
        """Cria a roleta do giro atual."""
        return Roulette(self.blinds()[1], self.rng)

    def pay_removal(self, roulette, key):
        """Paga com fichas da mesa para tirar ``key`` da roleta."""
        return _pay_removal(self.human, roulette, key)

    def grant(self, powerup):
        """Guarda o power-up sorteado e reinicia a contagem."""
        self.inventory.append(powerup)
        self.hands_until_spin = SPIN_EVERY

    def use_powerup(self, powerup, target=None):
        """Usa um power-up do inventário na mão atual."""
        result = self._use(self.human, self.inventory, self.active_effects, powerup, target)
        if result.ok:
            self.stats["powerups_used"] += 1
        return result

    def _use(self, player, inventory, effects, powerup, target):
        """Usa ``powerup`` por ``player``: sai de ``inventory`` e o nome vai para ``effects``."""
        ok, why = powerup.can_use(self.hand, player)
        if not ok:
            return UseResult(False, why)
        result = powerup.use(self.hand, player, target)
        if result.ok:
            inventory.remove(powerup)
            effects.append(powerup.name)
        return result

    def is_over(self):
        """Se a sessão acabou (as subclasses definem)."""
        return False


class CashSession(Session):
    """Cash game: as fichas valem dinheiro do saldo e você sai quando quiser.

    Bots que perdem tudo são trocados por bots novos, então a mesa nunca esvazia.
    """

    mode = "cash"

    def __init__(self, human_name, buy_in, difficulty, stake, rng=None, inventory=None):
        super().__init__(human_name, buy_in, difficulty, stake, rng, inventory)
        for seat in range(1, SEATS):
            self._new_bot(seat, self._bot_buy_in())

    def _bot_buy_in(self):
        """Fichas de um bot novo: de 60 a 150 big blinds."""
        return self.blinds()[1] * self.rng.choice((60, 80, 100, 100, 120, 150))

    def before_hand(self):
        """Troca os bots que não têm mais nem um big blind por bots novos."""
        bb = self.blinds()[1]
        for seat in range(1, SEATS):
            if self.players[seat].stack < bb:
                self._new_bot(seat, self._bot_buy_in())

    def rebuy(self, amount):
        """Recompra quando o jogador fica sem fichas."""
        self.human.stack += amount
        self.stats["rebought"] += amount

    def is_over(self):
        """O cash só acaba quando o jogador sai ou fica sem fichas."""
        return self.human.stack <= 0


class TournamentSession(Session):
    """Sit & Go de 6 jogadores: blinds sobem e ganha quem ficar com todas as fichas.

    Os dois primeiros lugares dividem o prêmio (65% e 35%).
    """

    mode = "tournament"
    START_STACK = 1500
    HANDS_PER_LEVEL = 8
    LEVELS = [(10, 20), (15, 30), (25, 50), (50, 100), (75, 150), (100, 200),
              (150, 300), (250, 500), (400, 800), (600, 1200), (1000, 2000)]
    PAYOUTS = [0.65, 0.35]

    def __init__(self, human_name, difficulty, stake, rng=None, inventory=None):
        super().__init__(human_name, self.START_STACK, difficulty, stake, rng, inventory)
        for seat in range(1, SEATS):
            self._new_bot(seat, self.START_STACK)
        self.buy_in = STAKES[stake]["buyin"]
        self.prize_pool = self.buy_in * SEATS
        self.finish_order = []
        self._stacks_before = {}

    @property
    def level(self):
        """Índice do nível de blinds atual."""
        return min(self.hands_played // self.HANDS_PER_LEVEL, len(self.LEVELS) - 1)

    def hands_to_next_level(self):
        """Mãos que faltam para os blinds subirem."""
        return self.HANDS_PER_LEVEL - self.hands_played % self.HANDS_PER_LEVEL

    def blinds(self):
        """Blinds do nível atual."""
        return self.LEVELS[self.level]

    def new_hand(self):
        """Guarda as fichas de cada um antes da mão (para desempatar eliminações)."""
        self._stacks_before = {p: p.stack for p in self.seated()}
        return super().new_hand()

    def end_hand(self):
        """Registra quem foi eliminado nesta mão."""
        super().end_hand()
        busted = [p for p in self.hand.players if p.stack == 0 and p not in self.finish_order]
        busted.sort(key=lambda p: self._stacks_before[p])
        self.finish_order.extend(busted)

    def remaining(self):
        """Jogadores ainda no torneio."""
        return self.seated()

    def place_of(self, player):
        """Colocação final de ``player`` (1 = campeão) ou ``None`` se ainda joga."""
        if player in self.finish_order:
            return SEATS - self.finish_order.index(player)
        if len(self.remaining()) == 1 and player.stack > 0:
            return 1
        return None

    def prize_for(self, place):
        """Prêmio para uma colocação."""
        if place is None or place > len(self.PAYOUTS):
            return 0
        return int(self.prize_pool * self.PAYOUTS[place - 1])

    def is_over(self):
        """Acaba quando o jogador cai ou quando só resta um jogador."""
        return self.human.stack == 0 or len(self.remaining()) <= 1
