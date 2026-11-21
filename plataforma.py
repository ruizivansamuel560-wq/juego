# -*- coding: utf-8 -*-
import pygame


class Plataforma:
    """Plataforma de un solo sentido (se puede atravesar desde abajo)."""
    movil = False

    def __init__(self, x, y, ancho, alto, textura):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.dx = 0  # desplazamiento de este frame (lo usa el jugador para ser "llevado")
        # Se repite la textura en bloques de 32 px en lugar de estirarla
        bloque = pygame.transform.scale(textura, (32, alto))
        self.textura = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        for bx in range(0, ancho, 32):
            self.textura.blit(bloque, (bx, 0))
        pygame.draw.line(self.textura, (255, 255, 255, 70), (0, 0), (ancho, 0), 2)

    def actualizar(self):
        self.dx = 0

    def dibujar(self, superficie):
        superficie.blit(self.textura, self.rect.topleft)


class PlataformaMovil(Plataforma):
    """Plataforma que oscila horizontalmente y arrastra al jugador."""
    movil = True

    def __init__(self, x, y, ancho, alto, textura, rango=120, vel=1.5):
        super().__init__(x, y, ancho, alto, textura)
        self.x0 = x
        self.rango = rango
        self.vel = vel
        self.dir = 1
        self.fx = float(x)
        pygame.draw.rect(self.textura, (0, 238, 255, 160), self.textura.get_rect(), 2)

    def actualizar(self):
        nuevo = self.fx + self.vel * self.dir
        if nuevo >= self.x0 + self.rango:
            nuevo = self.x0 + self.rango
            self.dir = -1
        elif nuevo <= self.x0:
            nuevo = self.x0
            self.dir = 1
        self.fx = nuevo
        nueva_x = int(round(nuevo))
        self.dx = nueva_x - self.rect.x
        self.rect.x = nueva_x
