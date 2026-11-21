# -*- coding: utf-8 -*-
"""Sistema de partículas con presets (salto, aterrizaje, moneda, muerte, impacto)."""
import math
import random

import pygame


class Particula:
    def __init__(self, x, y, color, vel_x=None, vel_y=None, radio=None,
                 gravedad=0.1, decaimiento=0.15, vida=None):
        self.x = x
        self.y = y
        self.vel_x = random.uniform(-4, 4) if vel_x is None else vel_x
        self.vel_y = random.uniform(-5, 2) if vel_y is None else vel_y
        self.radio = float(random.randint(4, 7) if radio is None else radio)
        self.color = color
        self.gravedad = gravedad
        self.decaimiento = decaimiento
        # vida en frames (opcional); si es None sólo muere por tamaño
        self.vida = vida
        self.vida_total = vida

    def actualizar(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y += self.gravedad
        self.vel_x *= 0.98
        self.radio -= self.decaimiento
        if self.vida is not None:
            self.vida -= 1
            if self.vida <= 0:
                self.radio = 0
        if self.radio < 0:
            self.radio = 0

    def dibujar(self, superficie, cam=(0, 0)):
        if self.radio > 0:
            pygame.draw.circle(superficie, self.color,
                               (int(self.x + cam[0]), int(self.y + cam[1])),
                               max(1, int(self.radio)))


class SistemaParticulas:
    """Contenedor + presets. Limita el total para mantener 60 FPS en el navegador."""
    MAX = 400

    def __init__(self):
        self.lista = []

    def _add(self, p):
        if len(self.lista) < self.MAX:
            self.lista.append(p)

    def limpiar(self):
        self.lista = []

    def actualizar(self):
        for p in self.lista:
            p.actualizar()
        self.lista = [p for p in self.lista if p.radio > 0]

    def dibujar(self, superficie, cam=(0, 0)):
        for p in self.lista:
            p.dibujar(superficie, cam)

    # ---------- Presets ----------
    def salto(self, x, y):
        for _ in range(7):
            self._add(Particula(x + random.uniform(-10, 10), y,
                                random.choice([(220, 220, 230), (180, 180, 195)]),
                                random.uniform(-1.8, 1.8), random.uniform(-1.2, 0.1),
                                random.randint(3, 5), 0.02, 0.18))

    def aterrizaje(self, x, y, fuerza=1.0):
        n = int(6 + 6 * min(fuerza, 1.5))
        for i in range(n):
            lado = -1 if i % 2 else 1
            self._add(Particula(x + random.uniform(-8, 8), y,
                                random.choice([(200, 190, 170), (160, 150, 130)]),
                                lado * random.uniform(0.8, 3.2), random.uniform(-1.6, -0.2),
                                random.randint(3, 6), 0.05, 0.2))

    def moneda(self, x, y):
        for i in range(14):
            a = (math.pi * 2 / 14) * i
            v = random.uniform(1.5, 3.5)
            self._add(Particula(x, y, random.choice([(255, 230, 80), (255, 255, 160), (255, 190, 30)]),
                                math.cos(a) * v, math.sin(a) * v, random.randint(3, 5), 0.0, 0.2))

    def impacto(self, x, y, n=16):
        for _ in range(n):
            self._add(Particula(x, y, random.choice([(255, 140, 0), (255, 215, 0), (255, 69, 0)])))

    def muerte_enemigo(self, x, y, grande=False):
        n = 40 if grande else 24
        for _ in range(n):
            a = random.uniform(0, math.pi * 2)
            v = random.uniform(1.5, 6 if grande else 4.5)
            self._add(Particula(x, y, random.choice([(255, 255, 255), (255, 80, 60), (255, 200, 60), (120, 255, 120)]),
                                math.cos(a) * v, math.sin(a) * v - 1, random.randint(4, 8),
                                0.12, 0.17))

    def danio(self, x, y):
        for _ in range(18):
            self._add(Particula(x, y, random.choice([(255, 40, 40), (255, 120, 120), (255, 255, 255)]),
                                random.uniform(-5, 5), random.uniform(-6, 1), random.randint(3, 6), 0.2, 0.2))

    def dash(self, x, y):
        self._add(Particula(x, y + random.randint(-10, 10), (0, 238, 255),
                            random.uniform(-0.5, 0.5), random.uniform(-0.3, 0.3),
                            random.randint(4, 7), 0.0, 0.3))

    def confeti(self, ancho):
        for _ in range(3):
            self._add(Particula(random.uniform(0, ancho), -6,
                                random.choice([(255, 215, 0), (0, 238, 255), (255, 90, 120), (120, 255, 140), (255, 255, 255)]),
                                random.uniform(-1.2, 1.2), random.uniform(1.2, 3.2), 5, 0.03, 0.0, 260))
