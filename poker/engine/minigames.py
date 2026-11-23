"""Regras dos mini games disputados entre as mãos.

A cada 2 mãos todos os jogadores disputam um mini game. Quem
vence escolhe a modalidade de poker das próximas mãos.

* **Escalada** (``climb``): aperte ESPAÇO o mais rápido possível; cada
  toque sobe um andar. Ganha quem chegar primeiro ao topo.
* **Corrida** (``race``): alterne as setas esquerda e direita para correr e aperte a seta para cima para pular
  as barreiras. Quem bate numa barreira fica tonto por um segundo.
* **Quiz** (``quiz``): 3 perguntas de conhecimentos gerais, 10 segundos
  cada. Acertar rápido vale mais pontos.

Este módulo não usa pygame: as regras ficam separadas da tela. Os bots não apertam teclas; o desempenho deles é sorteado
no começo (velocidade, erros) conforme a dificuldade.
"""

import random

GAME_KEYS = ["climb", "race", "quiz"]
GAME_INFO = {
    "climb": ("Escalada", "Aperte ESPAÇO o mais rápido que puder para subir o prédio!"),
    "race": ("Corrida", "Alterne as setas ESQUERDA e DIREITA para correr. Seta para CIMA pula as barreiras!"),
    "quiz": ("Quiz", "3 perguntas, 10 segundos cada. Responda com 1 a 4 ou clicando. Rápido vale mais!"),
}

CLIMB_GOAL = 60
CLIMB_LIMIT = 20.0
RACE_GOAL = 40
RACE_LIMIT = 25.0
HURDLES = (10, 20, 30)
AIR_TIME = 0.45
STUN_TIME = 1.0
QUIZ_QUESTIONS = 3
QUIZ_TIME = 10.0
QUIZ_REVEAL = 3.0
QUIZ_BASE_POINTS = 100
QUIZ_SPEED_POINTS = 100

BOT_SKILL = {
    "easy": {"climb": (4.6, 5.6), "race": (4.8, 5.6), "hurdle_fail": 0.45, "quiz_right": 0.5, "quiz_time": (3.0, 8.5)},
    "medium": {"climb": (5.8, 6.8), "race": (5.8, 6.8), "hurdle_fail": 0.25, "quiz_right": 0.7, "quiz_time": (2.2, 7.0)},
    "hard": {"climb": (7.0, 8.2), "race": (6.8, 7.8), "hurdle_fail": 0.1, "quiz_right": 0.85, "quiz_time": (1.5, 5.5)},
}

QUESTIONS = [
    ("Qual é o maior planeta do Sistema Solar?", "Júpiter", ["Saturno", "Terra", "Netuno"]),
    ("Quantos lados tem um hexágono?", "6", ["5", "7", "8"]),
    ("Qual é a capital da Austrália?", "Canberra", ["Sydney", "Melbourne", "Perth"]),
    ("Em que ano a frota de Cabral chegou ao Brasil?", "1500", ["1492", "1530", "1822"]),
    ("Qual é o símbolo químico do ouro?", "Au", ["Ag", "Go", "Or"]),
    ("Quem pintou a Mona Lisa?", "Leonardo da Vinci", ["Michelangelo", "Rafael", "Van Gogh"]),
    ("Qual é o maior oceano da Terra?", "Pacífico", ["Atlântico", "Índico", "Ártico"]),
    ("Quantos jogadores de cada time ficam em campo no futebol?", "11", ["9", "10", "12"]),
    ("Qual é o menor número primo?", "2", ["0", "1", "3"]),
    ("Em que continente fica o Egito?", "África", ["Ásia", "Europa", "Oceania"]),
    ("Quantos minutos tem uma hora e meia?", "90", ["60", "80", "120"]),
    ("Que gás as plantas absorvem na fotossíntese?", "Gás carbônico", ["Oxigênio", "Nitrogênio", "Hélio"]),
    ("Qual é o maior rio totalmente brasileiro?", "São Francisco", ["Amazonas", "Paraná", "Tietê"]),
    ("Quem escreveu \"Dom Casmurro\"?", "Machado de Assis", ["José de Alencar", "Clarice Lispector", "Jorge Amado"]),
    ("Quanto é 7 x 8?", "56", ["54", "58", "64"]),
    ("Qual é a capital do Canadá?", "Ottawa", ["Toronto", "Vancouver", "Montreal"]),
    ("Em que ano o ser humano pisou na Lua pela primeira vez?", "1969", ["1959", "1965", "1972"]),
    ("Qual é o osso mais longo do corpo humano?", "Fêmur", ["Úmero", "Tíbia", "Rádio"]),
    ("Quantos estados tem o Brasil (sem contar o Distrito Federal)?", "26", ["24", "25", "27"]),
    ("Qual é a fórmula química da água?", "H2O", ["CO2", "O2", "H2O2"]),
    ("Qual é o país mais populoso do mundo hoje?", "Índia", ["China", "Estados Unidos", "Indonésia"]),
    ("Qual é a velocidade aproximada da luz no vácuo?", "300 mil km/s", ["30 mil km/s", "3 mil km/s", "3 milhões de km/s"]),
    ("Quem formulou a teoria da relatividade?", "Albert Einstein", ["Isaac Newton", "Galileu Galilei", "Nikola Tesla"]),
    ("Quantos bits tem um byte?", "8", ["4", "16", "32"]),
    ("Qual é a capital do Japão?", "Tóquio", ["Quioto", "Osaka", "Hiroshima"]),
    ("Qual é o maior animal do mundo?", "Baleia-azul", ["Elefante-africano", "Girafa", "Cachalote"]),
    ("Em que linguagem de programação este jogo foi feito?", "Python", ["Java", "C++", "JavaScript"]),
    ("Em que país ficam as pirâmides de Gizé?", "Egito", ["México", "Peru", "Sudão"]),
    ("Qual é o planeta mais próximo do Sol?", "Mercúrio", ["Vênus", "Marte", "Terra"]),
    ("Qual é a raiz quadrada de 144?", "12", ["11", "13", "14"]),
    ("Quantas teclas tem um piano padrão?", "88", ["66", "76", "100"]),
    ("Qual é a moeda do Japão?", "Iene", ["Yuan", "Won", "Rupia"]),
    ("Em que cidade fica o Cristo Redentor?", "Rio de Janeiro", ["São Paulo", "Salvador", "Brasília"]),
    ("Qual é o maior país do mundo em área?", "Rússia", ["Canadá", "China", "Brasil"]),
    ("Quantas cartas tem um baralho comum, sem coringas?", "52", ["48", "50", "54"]),
    ("No poker, qual destas mãos é a mais forte?", "Flush", ["Sequência", "Trinca", "Dois pares"]),
    ("Quanto vale a soma dos ângulos internos de um triângulo?", "180 graus", ["90 graus", "270 graus", "360 graus"]),
    ("Qual é a capital da Argentina?", "Buenos Aires", ["Montevidéu", "Santiago", "Lima"]),
    ("Quem foi o primeiro presidente do Brasil?", "Deodoro da Fonseca", ["Getúlio Vargas", "Floriano Peixoto", "Prudente de Morais"]),
    ("Qual elemento químico tem o símbolo Fe?", "Ferro", ["Flúor", "Fósforo", "Férmio"]),
    ("Quantos dias tem um ano bissexto?", "366", ["364", "365", "367"]),
    ("Qual metal é líquido em temperatura ambiente?", "Mercúrio", ["Chumbo", "Alumínio", "Sódio"]),
    ("Qual seleção venceu a Copa do Mundo de 2002?", "Brasil", ["Alemanha", "França", "Itália"]),
    ("Qual planeta é conhecido como planeta vermelho?", "Marte", ["Júpiter", "Vênus", "Saturno"]),
    ("Quanto vale o número binário 101 em decimal?", "5", ["3", "6", "10"]),
]


def _bot_skill(participant):
    """Tabela de desempenho da dificuldade do bot (médio se for desconhecida)."""
    return BOT_SKILL.get(participant["difficulty"], BOT_SKILL["medium"])


def quiz_points(correct, used):
    """Pontos de uma resposta: acerto vale 100 + até 100 de bônus pela rapidez."""
    if not correct:
        return 0
    left = max(0.0, QUIZ_TIME - used)
    return int(round(QUIZ_BASE_POINTS + QUIZ_SPEED_POINTS * left / QUIZ_TIME))


class Runner:
    """Corredor controlado pelo teclado (a parte "física" da corrida do jogador).

    Cada tecla alternada (esquerda depois direita, ou o contrário) avança um passo. Passar
    por uma barreira sem estar no ar deixa o corredor tonto por ``STUN_TIME``.
    """

    def __init__(self):
        self.pos = 0
        self.last = None
        self.air_until = -1.0
        self.stun_until = -1.0
        self.cleared = set()

    def press(self, side, now):
        """``side`` é ``"left"`` ou ``"right"``. Repetir o mesmo lado não anda."""
        if now < self.stun_until or self.pos >= RACE_GOAL or side == self.last:
            return
        self.last = side
        self.pos += 1
        for h in HURDLES:
            if h not in self.cleared and self.pos >= h:
                self.cleared.add(h)
                if now >= self.air_until:
                    self.stun_until = now + STUN_TIME

    def jump(self, now):
        """Pula (se não estiver no ar nem tonto)."""
        if now >= self.air_until and now >= self.stun_until:
            self.air_until = now + AIR_TIME

    def airborne(self, now):
        """Se está no ar (pulando) agora."""
        return now < self.air_until

    def stunned(self, now):
        """Se está tonto (parado) agora."""
        return now < self.stun_until


class MiniGameRound:
    """Uma disputa de mini game.

    Args:
        key: ``"climb"``, ``"race"`` ou ``"quiz"``.
        participants: lista de dicionários com ``seat``, ``name``, ``bot``,
            ``difficulty`` e ``color``.
        seed: semente do sorteio (perguntas e desempenho dos bots).
    """

    def __init__(self, key, participants, seed):
        self.key = key
        self.participants = participants
        self.rng = random.Random(seed)
        self.start_time = None
        self.over = False

    def start(self, now):
        """Começa a contar o tempo da disputa."""
        self.start_time = now

    def elapsed(self, now):
        """Segundos desde o começo (0 se ainda não começou)."""
        return 0.0 if self.start_time is None else max(0.0, now - self.start_time)

    def bots(self):
        """Participantes que são bots."""
        return [p for p in self.participants if p["bot"]]

    def winner(self):
        """Assento de quem venceu."""
        return self.standings()[0][0]

    def tick(self, now):
        """Avança o tempo (bots jogam, fases mudam)."""

    def standings(self):
        """Lista ``(assento, texto_do_resultado)`` do primeiro ao último."""
        raise NotImplementedError

    def state(self, now):
        """Dicionário (que vira JSON) com o que a tela precisa desenhar."""
        raise NotImplementedError


class ProgressRound(MiniGameRound):
    """Escalada e corrida: ganha quem chegar primeiro ao fim."""

    def __init__(self, key, participants, seed):
        super().__init__(key, participants, seed)
        self.goal = CLIMB_GOAL if key == "climb" else RACE_GOAL
        self.limit = CLIMB_LIMIT if key == "climb" else RACE_LIMIT
        self.progress = {p["seat"]: 0.0 for p in participants}
        self.finish = {}
        self.plans = {}
        for p in self.bots():
            skill = _bot_skill(p)
            speed = self.rng.uniform(*skill[key])
            fails = [h for h in HURDLES if self.rng.random() < skill["hurdle_fail"]] if key == "race" else []
            self.plans[p["seat"]] = (speed, fails)

    def bot_progress(self, seat, t):
        """Posição de um bot no instante ``t``: anda com velocidade fixa e para nas barreiras em que erra."""
        speed, fails = self.plans[seat]
        lost = 0.0
        for h in fails:
            if (t - lost) * speed >= h:
                lost += min(STUN_TIME, t - lost - h / speed)
        return min(float(self.goal), (t - lost) * speed)

    def bot_finish_time(self, seat):
        """Quando o bot chega ao fim: tempo correndo mais o tempo tonto."""
        speed, fails = self.plans[seat]
        return self.goal / speed + STUN_TIME * len(fails)

    def set_progress(self, seat, value, now):
        """Atualiza a posição de uma pessoa (vem do teclado dela)."""
        if self.over or seat not in self.progress or seat in self.finish:
            return
        value = max(self.progress[seat], min(float(self.goal), float(value)))
        self.progress[seat] = value
        if value >= self.goal:
            self.finish[seat] = self.elapsed(now)

    def tick(self, now):
        """Move os bots e termina quando todos chegam ou o tempo acaba."""
        if self.start_time is None or self.over:
            return
        t = self.elapsed(now)
        for seat in self.plans:
            self.progress[seat] = self.bot_progress(seat, t)
            if seat not in self.finish and self.progress[seat] >= self.goal:
                self.finish[seat] = self.bot_finish_time(seat)
        if len(self.finish) == len(self.participants) or t >= self.limit:
            self.over = True

    def standings(self):
        """Quem chegou vem antes (pelo tempo); depois, quem foi mais longe."""
        def order(p):
            seat = p["seat"]
            if seat in self.finish:
                return (0, self.finish[seat])
            return (1, -self.progress[seat])

        result = []
        for p in sorted(self.participants, key=order):
            seat = p["seat"]
            label = f"{self.finish[seat]:.1f} s" if seat in self.finish else f"{self.progress[seat] / self.goal:.0%}"
            result.append((seat, label))
        return result

    def state(self, now):
        """Posições, chegadas e tempo restante."""
        return {
            "progress": [[seat, value] for seat, value in self.progress.items()],
            "finish": [[seat, value] for seat, value in self.finish.items()],
            "time_left": max(0.0, self.limit - self.elapsed(now)),
            "over": self.over,
        }


class QuizRound(MiniGameRound):
    """Quiz de 3 perguntas. Fases: ``question`` (10 s ou até todos responderem) e ``reveal``."""

    def __init__(self, key, participants, seed):
        super().__init__(key, participants, seed)
        self.questions = []
        for text, right, wrong in self.rng.sample(QUESTIONS, QUIZ_QUESTIONS):
            options = [right] + list(wrong)
            self.rng.shuffle(options)
            self.questions.append({"text": text, "options": options, "correct": options.index(right)})
        self.index = 0
        self.phase = "question"
        self.phase_start = None
        self.answers = [{} for _ in self.questions]
        self.totals = {p["seat"]: 0 for p in participants}
        self.plans = {}
        for p in self.bots():
            skill = _bot_skill(p)
            plan = []
            for q in self.questions:
                right = self.rng.random() < skill["quiz_right"]
                wrong = [i for i in range(4) if i != q["correct"]]
                plan.append((q["correct"] if right else self.rng.choice(wrong), self.rng.uniform(*skill["quiz_time"])))
            self.plans[p["seat"]] = plan

    def start(self, now):
        """Começa a primeira pergunta."""
        super().start(now)
        self.phase_start = now

    def answer(self, seat, choice, now):
        """Resposta de uma pessoa para a pergunta atual (só vale a primeira)."""
        if self.over or self.phase != "question" or seat not in self.totals:
            return
        current = self.answers[self.index]
        if seat in current or not isinstance(choice, int) or not 0 <= choice < 4:
            return
        current[seat] = (choice, min(QUIZ_TIME, now - self.phase_start))

    def tick(self, now):
        """Bots respondem; a pergunta fecha (e pontua) e depois passa para a próxima."""
        if self.start_time is None or self.over:
            return
        t = now - self.phase_start
        current = self.answers[self.index]
        if self.phase == "question":
            for seat, plan in self.plans.items():
                choice, when = plan[self.index]
                if seat not in current and t >= when:
                    current[seat] = (choice, when)
            if len(current) == len(self.participants) or t >= QUIZ_TIME:
                correct = self.questions[self.index]["correct"]
                for seat, (choice, used) in current.items():
                    self.totals[seat] += quiz_points(choice == correct, used)
                self.phase = "reveal"
                self.phase_start = now
        elif t >= QUIZ_REVEAL:
            if self.index + 1 >= len(self.questions):
                self.over = True
            else:
                self.index += 1
                self.phase = "question"
                self.phase_start = now

    def standings(self):
        """Do maior para o menor total de pontos."""
        ordered = sorted(self.participants, key=lambda p: -self.totals[p["seat"]])
        return [(p["seat"], f"{self.totals[p['seat']]} pts") for p in ordered]

    def state(self, now):
        """Pergunta atual, quem já respondeu e, na revelação, a resposta certa."""
        q = self.questions[self.index]
        current = self.answers[self.index]
        limit = QUIZ_TIME if self.phase == "question" else QUIZ_REVEAL
        state = {
            "index": self.index,
            "phase": self.phase,
            "time_left": max(0.0, limit - (now - (self.phase_start or now))),
            "text": q["text"],
            "options": q["options"],
            "answered": sorted(current),
            "totals": [[seat, pts] for seat, pts in self.totals.items()],
            "over": self.over,
        }
        if self.phase == "reveal":
            state["correct"] = q["correct"]
            state["picks"] = [[seat, choice, quiz_points(choice == q["correct"], used)]
                              for seat, (choice, used) in current.items()]
        return state


def create_round(key, participants, seed):
    """Cria a disputa certa para ``key``."""
    if key == "quiz":
        return QuizRound(key, participants, seed)
    return ProgressRound(key, participants, seed)
