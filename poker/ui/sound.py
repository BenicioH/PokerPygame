"""Efeitos sonoros e música, gerados por código (síntese).

Nenhum arquivo de áudio é necessário: cada som é montado amostra por
amostra a partir de ondas senoidais, triangulares e ruído, com um envelope
de volume (ataque e decaimento). Isso evita problemas de direitos autorais
e deixa o projeto leve.

Se o computador não tiver saída de som, o gerenciador fica desligado e
todas as chamadas viram "não faz nada".
"""

import array
import math
import random

import pygame

RATE = 22050
NOISE_RNG = random.Random(7)


def _env(i, n, attack=0.005, release=None):
    """Envelope simples: sobe rápido no início e decai até o fim."""
    t = i / RATE
    a = min(1.0, t / attack) if attack else 1.0
    if release is None:
        return a * (1 - i / n) ** 2
    return a * math.exp(-t / release)


def _tone(freq, dur, wave="sine", release=None, volume=1.0, sweep=0.0):
    """Gera uma nota. ``sweep`` muda a frequência ao longo da nota (Hz por segundo)."""
    n = int(RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        f = freq + sweep * i / RATE
        phase += f / RATE
        x = phase % 1.0
        if wave == "sine":
            v = math.sin(2 * math.pi * x)
        elif wave == "triangle":
            v = 4 * abs(x - 0.5) - 1
        else:
            v = 1.0 if x < 0.5 else -1.0
        out.append(v * _env(i, n, release=release) * volume)
    return out


def _noise(dur, smooth=1, volume=1.0, release=None):
    """Ruído branco suavizado (média móvel), bom para cartas e fichas."""
    n = int(RATE * dur)
    out = []
    acc = 0.0
    for i in range(n):
        acc += (NOISE_RNG.uniform(-1, 1) - acc) / smooth
        out.append(acc * _env(i, n, release=release) * volume)
    return out


def _mix(*parts):
    """Soma partes ``(início_em_segundos, amostras)`` em uma só faixa."""
    length = max(int(start * RATE) + len(s) for start, s in parts)
    out = [0.0] * length
    for start, samples in parts:
        offset = int(start * RATE)
        for i, v in enumerate(samples):
            out[offset + i] += v
    return out


class SoundManager:
    """Carrega (sintetiza) e toca os sons do jogo."""

    def __init__(self, sfx=True, music=True):
        self.sfx_on = sfx
        self.music_on = music
        self.sounds = {}
        self.music = None
        self.channels = 1
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            _, _, self.channels = pygame.mixer.get_init()
            self._build()
            self.available = True
        except (pygame.error, TypeError, ValueError):
            self.available = False

    def _sound(self, samples, volume=0.5):
        """Converte amostras (-1 a 1) em um ``pygame.mixer.Sound``."""
        data = array.array("h")
        for v in samples:
            value = int(max(-1.0, min(1.0, v * volume)) * 32767)
            for _ in range(self.channels):
                data.append(value)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _build(self):
        """Cria todos os efeitos sonoros."""
        s = self.sounds
        s["click"] = self._sound(_tone(900, 0.04, release=0.01), 0.35)
        s["card"] = self._sound(_noise(0.09, smooth=3, release=0.025), 0.45)
        s["chip"] = self._sound(_mix(
            (0.0, _tone(3100, 0.03, release=0.006)),
            (0.035, _tone(2600, 0.03, release=0.006)),
            (0.065, _tone(3400, 0.03, release=0.005)),
        ), 0.35)
        s["check"] = self._sound(_mix(
            (0.0, _tone(160, 0.06, release=0.015)),
            (0.09, _tone(150, 0.06, release=0.015)),
        ), 0.7)
        s["fold"] = self._sound(_noise(0.22, smooth=6, release=0.08), 0.5)
        s["win"] = self._sound(_mix(*[
            (i * 0.09, _tone(f, 0.35, "triangle", release=0.12))
            for i, f in enumerate((523, 659, 784, 1046))
        ]), 0.35)
        s["lose"] = self._sound(_mix(
            (0.0, _tone(392, 0.25, "triangle", release=0.1)),
            (0.18, _tone(311, 0.4, "triangle", release=0.15)),
        ), 0.3)
        s["tick"] = self._sound(_tone(1500, 0.015, release=0.004), 0.3)
        s["powerup"] = self._sound(_mix(
            (0.0, _tone(400, 0.3, "sine", release=0.15, sweep=2600)),
            (0.05, _tone(800, 0.3, "triangle", release=0.12, sweep=2600, volume=0.4)),
        ), 0.35)
        s["reward"] = self._sound(_mix(*[
            (i * 0.11, _tone(f, 0.5, "triangle", release=0.2))
            for i, f in enumerate((392, 523, 659, 784, 1046))
        ]), 0.32)
        s["turn"] = self._sound(_tone(880, 0.35, release=0.1), 0.25)
        s["error"] = self._sound(_tone(120, 0.12, "square", release=0.05), 0.15)
        self.music = self._sound(self._music_loop(), 0.16)

    def _music_loop(self):
        """Música ambiente em laço: quatro acordes suaves com baixo."""
        chords = [
            (110.0, [220.0, 261.6, 329.6, 392.0]),
            (146.8, [220.0, 261.6, 349.2, 293.7]),
            (98.0, [246.9, 293.7, 349.2, 392.0]),
            (130.8, [246.9, 329.6, 392.0, 261.6]),
        ]
        chord_len = 2.4
        n = int(RATE * chord_len)
        out = []
        for bass, notes in chords:
            for i in range(n):
                t = i / RATE
                fade = min(1.0, t / 0.4) * min(1.0, (chord_len - t) / 0.4)
                v = sum(math.sin(2 * math.pi * f * t) * 0.16 for f in notes)
                v += math.sin(2 * math.pi * bass * t) * 0.3 * math.exp(-t / 1.2)
                v *= 0.85 + 0.15 * math.sin(2 * math.pi * t / chord_len * 2)
                out.append(v * fade)
        return out

    def play(self, name):
        """Toca um efeito, se os efeitos estiverem ligados."""
        if self.available and self.sfx_on and name in self.sounds:
            self.sounds[name].play()

    def start_music(self):
        """Começa a música em laço (se estiver ligada)."""
        if self.available and self.music_on and self.music.get_num_channels() == 0:
            self.music.play(loops=-1, fade_ms=1500)

    def set_music(self, on):
        """Liga ou desliga a música."""
        self.music_on = on
        if not self.available:
            return
        if on:
            self.start_music()
        else:
            self.music.fadeout(500)

    def set_sfx(self, on):
        """Liga ou desliga os efeitos sonoros."""
        self.sfx_on = on
