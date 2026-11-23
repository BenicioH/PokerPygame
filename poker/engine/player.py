"""Jogador sentado em uma mesa (humano ou bot)."""


class Player:
    """Estado de um jogador.

    O mesmo objeto acompanha o jogador por várias mãos. O que vale só para a
    mão atual (cartas, apostas, se desistiu) é zerado em :meth:`reset_for_hand`.

    Atributos:
        name: nome exibido na mesa.
        stack: fichas na frente do jogador (fora do pote).
        is_human: verdadeiro para o jogador que usa o teclado e o mouse.
        bot: estratégia de decisão (``None`` para humanos).
        color: cor do avatar; seat: assento na mesa (0 a 5).
        hole: as duas cartas fechadas.
        bet: quanto o jogador colocou na rodada de apostas atual.
        committed: quanto colocou no pote na mão inteira.
        folded / all_in: situação na mão atual.
        has_acted: se já agiu desde a última aposta ou aumento.
        last_action: texto curto da última ação, mostrado na mesa.
        show_cards: se as cartas ficam abertas para todos (all-in ou showdown).
        revealed: índices das cartas reveladas pelo power-up Leitura.
    """

    def __init__(self, name, stack, is_human=False, bot=None, color=(120, 120, 120)):
        self.name = name
        self.stack = stack
        self.is_human = is_human
        self.bot = bot
        self.color = color
        self.seat = 0
        self.reset_for_hand()

    def reset_for_hand(self):
        """Limpa tudo o que pertence só à mão anterior."""
        self.hole = []
        self.bet = 0
        self.committed = 0
        self.folded = False
        self.all_in = False
        self.has_acted = False
        self.last_action = ""
        self.show_cards = False
        self.revealed = set()

    @property
    def in_hand(self):
        """Ainda disputa o pote (não desistiu)."""
        return not self.folded and bool(self.hole)

    @property
    def can_act(self):
        """Ainda pode tomar decisões (não desistiu e não está all-in)."""
        return self.in_hand and not self.all_in

    def put_chips(self, amount):
        """Move fichas do stack para a aposta, limitado ao que o jogador tem.

        Retorna:
            Quanto foi realmente apostado.
        """
        amount = min(amount, self.stack)
        self.stack -= amount
        self.bet += amount
        self.committed += amount
        if self.stack == 0:
            self.all_in = True
        return amount

    def __repr__(self):
        return f"Player({self.name!r}, stack={self.stack})"
