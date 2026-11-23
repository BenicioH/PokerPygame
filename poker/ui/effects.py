"""Animações: objetos voando pela mesa, textos que sobem e partículas."""

import math
import random

import pygame

from . import draw


def ease_out_cubic(t):
    """Começa rápido e desacelera no fim (0 a 1 -> 0 a 1)."""
    return 1 - (1 - t) ** 3


class Flight:
    """Algo que voa de ``start`` até ``end`` (uma carta, uma pilha de fichas).

    Args:
        duration: duração do voo em segundos.
        delay: espera antes de começar (para distribuir cartas uma a uma).
        kind: ``"card"``, ``"face"`` (carta aberta) ou ``"chips"``.
        payload: carta ou quantidade de fichas a desenhar.
        on_land: função chamada quando o voo termina.
        arc: altura da curva do voo em pixels.
    """

    def __init__(self, start, end, duration, delay=0.0, kind="card", payload=None, on_land=None, arc=0):
        self.start = start
        self.end = end
        self.duration = duration
        self.delay = delay
        self.kind = kind
        self.payload = payload
        self.on_land = on_land
        self.arc = arc
        self.time = 0.0
        self.done = False

    @property
    def started(self):
        """Se o atraso inicial já passou."""
        return self.time >= self.delay

    @property
    def progress(self):
        """Progresso de 0 a 1 do voo."""
        return max(0.0, min(1.0, (self.time - self.delay) / self.duration))

    @property
    def pos(self):
        """Posição atual, com desaceleração e arco opcional."""
        t = ease_out_cubic(self.progress)
        x = self.start[0] + (self.end[0] - self.start[0]) * t
        y = self.start[1] + (self.end[1] - self.start[1]) * t - math.sin(math.pi * t) * self.arc
        return (x, y)

    def update(self, dt):
        """Avança o tempo; chama ``on_land`` uma vez no fim."""
        self.time += dt
        if not self.done and self.progress >= 1.0:
            self.done = True
            if self.on_land:
                self.on_land()
        return self.done


class FloatText:
    """Texto que sobe e some (por exemplo "+340" em cima de quem ganhou)."""

    def __init__(self, value, pos, color, size=30, duration=1.4):
        self.value = value
        self.pos = pos
        self.color = color
        self.size = size
        self.duration = duration
        self.time = 0.0

    def update(self, dt):
        """Avança o tempo. Devolve ``True`` quando o texto já sumiu."""
        self.time += dt
        return self.time >= self.duration

    def draw(self, surface):
        """Desenha o texto subindo e ficando transparente."""
        t = self.time / self.duration
        surf = draw.text_surface(self.value, self.size, self.color, True).copy()
        surf.set_alpha(int(255 * (1 - t ** 2)))
        surface.blit(surf, surf.get_rect(center=(self.pos[0], self.pos[1] - 50 * ease_out_cubic(t))))


class Particles:
    """Confete simples para comemorar vitórias e power-ups."""

    def __init__(self):
        self.items = []
        self.rng = random.Random()

    def burst(self, pos, colors, count=40, speed=260):
        """Solta ``count`` partículas a partir de ``pos``."""
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(speed * 0.3, speed)
            self.items.append([pos[0], pos[1], math.cos(angle) * v, math.sin(angle) * v - 120,
                               self.rng.uniform(0.6, 1.2), self.rng.choice(colors), self.rng.randint(3, 6)])

    def update(self, dt):
        """Move as partículas com gravidade e remove as que acabaram."""
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 420 * dt
            p[2] *= 0.98
            p[4] -= dt
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, surface):
        """Desenha cada partícula como um quadradinho que encolhe no fim da vida."""
        for x, y, _, _, life, color, size in self.items:
            if life < 0.3:
                size = max(1, int(size * life / 0.3))
            pygame.draw.rect(surface, color, (int(x), int(y), size, size))
