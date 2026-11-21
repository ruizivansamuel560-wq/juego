# -*- coding: utf-8 -*-
"""Efectos de sonido 100% procedurales (sin archivos externos).
Se generan con array + pygame.mixer.Sound(buffer=...) adaptándose al formato real del mixer.
Si el audio no está disponible el juego sigue funcionando en silencio."""
import array
import math
import random

import pygame


def _tono(freq, f0, f1, dur, forma="seno", ruido=0.0):
    n = int(freq * dur)
    out = []
    fase = 0.0
    for i in range(n):
        t = i / max(1, n - 1)
        fase += 2 * math.pi * (f0 + (f1 - f0) * t) / freq
        s = (1.0 if math.sin(fase) >= 0 else -1.0) if forma == "cuadrada" else math.sin(fase)
        s = s * (1 - ruido) + random.uniform(-1, 1) * ruido
        out.append(s * (1.0 - t) ** 1.5)  # decaimiento
    return out


class Sonidos:
    def __init__(self):
        self.ok = False
        self.s = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            freq, size, canales = pygame.mixer.get_init()
            if size != -16:
                return  # formato no soportado por el generador: sin sonido
            self.freq, self.canales = freq, max(1, canales)
            self.ok = True
        except Exception:
            self.ok = False
            return

        def t(f0, f1, dur, forma="seno", ruido=0.0):
            return _tono(self.freq, f0, f1, dur, forma, ruido)

        c = "cuadrada"
        self.s["salto"] = self._crear(t(260, 620, 0.14, c), 0.18)
        self.s["aterrizaje"] = self._crear(t(110, 50, 0.08, "seno", 0.4), 0.30)
        self.s["moneda"] = self._crear(t(880, 1320, 0.12, c) + t(1320, 1760, 0.14, c), 0.16)
        self.s["golpe"] = self._crear(t(300, 90, 0.12, c, 0.5), 0.25)
        self.s["muerte_enemigo"] = self._crear(t(500, 60, 0.28, c, 0.35), 0.25)
        self.s["danio"] = self._crear(t(220, 55, 0.30, c, 0.6), 0.30)
        self.s["dash"] = self._crear(t(900, 200, 0.16, "seno", 0.7), 0.20)
        self.s["menu"] = self._crear(t(520, 780, 0.10, c), 0.15)
        self.s["nivel"] = self._crear(t(523, 523, 0.10, c) + t(659, 659, 0.10, c) + t(784, 784, 0.18, c), 0.18)
        self.s["gameover"] = self._crear(t(400, 80, 0.70, c, 0.2), 0.25)
        self.s["victoria"] = self._crear(t(523, 523, 0.12, c) + t(659, 659, 0.12, c) +
                                         t(784, 784, 0.12, c) + t(1047, 1047, 0.30, c), 0.20)

    def _crear(self, muestras, volumen):
        try:
            buf = array.array("h")
            for m in muestras:
                v = int(max(-1.0, min(1.0, m)) * 32767 * volumen)
                for _ in range(self.canales):
                    buf.append(v)
            return pygame.mixer.Sound(buffer=buf.tobytes())
        except Exception:
            return None

    def play(self, nombre):
        snd = self.s.get(nombre) if self.ok else None
        if snd:
            try:
                snd.play()
            except Exception:
                pass
