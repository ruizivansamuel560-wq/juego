# -*- coding: utf-8 -*-
import math

import pygame

import recursos


class Objeto:
    """Objetos del nivel: moneda, picos, picos_ciclo (trampa intermitente) y pocion."""
    # Ciclo de la trampa intermitente (ms de juego)
    PERIODO = 3000
    OCULTO = 1400   # [0, 1400): escondidos
    AVISO = 1900    # [1400, 1900): parpadean avisando, sin dañar; después, activos

    def __init__(self, x, y, tipo, ruta_assets, fase=0):
        self.x = x
        self.y = y
        self.tipo = tipo
        self.activo = True
        self.indice_anim = 0.0
        self.fase = fase
        self.fase_ciclo = 0  # 0 oculto, 1 aviso, 2 activo
        self.ahora = 0.0
        r = recursos.obtener(ruta_assets)

        if tipo == "moneda":
            self.ancho, self.alto = 25, 25
            self.anim = r.frames("coin_anim_strip_6.png", 6, tam=(25, 25))
        elif tipo in ("picos", "picos_ciclo"):
            self.ancho, self.alto = 40, 30
            img = pygame.transform.scale(r.imagen("spikes.png"), (self.ancho, self.alto))
            self.imagen = pygame.transform.flip(img, False, True)
            if tipo == "picos_ciclo":
                self.imagen_aviso = self.imagen.copy()
                self.imagen_aviso.set_alpha(110)
        elif tipo == "pocion":
            self.ancho, self.alto = 24, 30
            self.imagen = pygame.transform.scale(r.imagen("health_potion.png"), (self.ancho, self.alto))

    @property
    def rect(self):
        if self.tipo in ("picos", "picos_ciclo"):
            return pygame.Rect(self.x + 6, self.y + 12, self.ancho - 12, self.alto - 12)
        return pygame.Rect(self.x, self.y, self.ancho, self.alto)

    @property
    def peligroso(self):
        if self.tipo == "picos":
            return True
        return self.tipo == "picos_ciclo" and self.fase_ciclo == 2

    def actualizar(self, ahora=0.0):
        self.ahora = ahora
        if self.tipo == "moneda":
            self.indice_anim += 0.15
            if self.indice_anim >= len(self.anim):
                self.indice_anim = 0.0
        elif self.tipo == "picos_ciclo":
            t = (ahora + self.fase) % self.PERIODO
            self.fase_ciclo = 0 if t < self.OCULTO else (1 if t < self.AVISO else 2)

    def dibujar(self, superficie):
        if not self.activo:
            return
        if self.tipo == "moneda":
            bob = math.sin(self.ahora / 220.0 + self.x) * 3
            superficie.blit(self.anim[int(self.indice_anim)], (self.x, self.y + bob))
        elif self.tipo == "picos":
            superficie.blit(self.imagen, (self.x, self.y))
        elif self.tipo == "picos_ciclo":
            base = (self.x, self.y + self.alto - 4, self.ancho, 4)
            pygame.draw.rect(superficie, (70, 40, 40), base)
            if self.fase_ciclo == 1:
                if int(self.ahora / 70) % 2 == 0:
                    superficie.blit(self.imagen_aviso, (self.x + (int(self.ahora / 35) % 3 - 1), self.y))
            elif self.fase_ciclo == 2:
                superficie.blit(self.imagen, (self.x, self.y))
        elif self.tipo == "pocion":
            bob = math.sin(self.ahora / 260.0 + self.x) * 3
            superficie.blit(self.imagen, (self.x, self.y + bob))
