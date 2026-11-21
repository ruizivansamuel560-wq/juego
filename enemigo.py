# -*- coding: utf-8 -*-
import math
import random

import pygame

import recursos

# tam, vel, vida, (archivo, cuadros), visión (px), velocidad de animación
TIPOS = {
    "slime":      dict(tam=(45, 35),   vel=1.6, vida=1,  img=("slime_walk_anim_strip_15.png", 15), vision=170, anim=0.15),
    "hongo":      dict(tam=(40, 45),   vel=2.2, vida=1,  img=("mushroom_walk_anim_strip_8.png", 8), vision=230, anim=0.15),
    "mosca":      dict(tam=(38, 32),   vel=1.9, vida=1,  img=("orange_fly_idle_or_flying_anim_strip_3.png", 3), vision=260, anim=0.25),
    "jefe1":      dict(tam=(90, 95),   vel=2.0, vida=5,  img=("goblin_run_anim_strip_6.png", 6), vision=9999, anim=0.15),
    "jefe2":      dict(tam=(110, 45),  vel=1.8, vida=7,  img=("worm_spritesheet.png", 3), vision=9999, anim=0.10),
    # El spritesheet del bombardero es una cuadrícula; se usa su tira de idle (existe en assets)
    "jefe_final": dict(tam=(120, 120), vel=3.0, vida=10, img=("bomber_goblin_idle_anim_strip_4.png", 4), vision=9999, anim=0.15),
}
_CACHE = {}


def _graficos(tipo, ruta_assets):
    if tipo not in _CACHE:
        d = TIPOS[tipo]
        r = recursos.obtener(ruta_assets)
        frames = r.frames(d["img"][0], d["img"][1], tam=d["tam"])
        flip = [pygame.transform.flip(f, True, False) for f in frames]
        _CACHE[tipo] = (frames, flip, r.siluetas_blancas(frames), r.siluetas_blancas(flip))
    return _CACHE[tipo]


class Enemigo:
    def __init__(self, x, y, tipo, ruta_assets, dificultad=1.0):
        d = TIPOS[tipo]
        self.x = float(x)
        self.y = float(y)
        self.tipo = tipo
        self.ancho, self.alto = d["tam"]
        self.es_jefe = tipo.startswith("jefe")
        self.volador = tipo == "mosca"
        f = 1 + (dificultad - 1) * 0.4
        self.dificultad = dificultad
        self.vel_x = d["vel"] * f
        self.vision = d["vision"] * min(dificultad, 1.6)
        self.vida_max = self.vida = d["vida"]
        self.velocidad_anim = d["anim"]
        self.vivo = True
        self.direccion = random.choice([-1, 1])
        self.estado = "patrulla"
        self.vel_y = 0.0
        self.gravedad = 0.6
        self.en_suelo = False
        self.flash = 0
        self.aturdido = 0
        self.kb_x = 0.0
        self.cd = random.randint(70, 150)
        self.t_estado = 0
        self.salto_dir = 1
        self.home_x, self.home_y = self.x, self.y
        self.fase = random.random() * 6.28
        self.indice_anim = 0.0
        self.frames, self.frames_flip, self.blancos, self.blancos_flip = _graficos(tipo, ruta_assets)

    # ---------------------------------------------------------------- utilidades
    @property
    def rect(self):
        """Hitbox algo menor que el sprite (colisiones más justas)."""
        return pygame.Rect(int(self.x), int(self.y), self.ancho, self.alto).inflate(
            -int(self.ancho * 0.2), -int(self.alto * 0.1))

    def recibir_golpe(self, dirx=0):
        """Devuelve True si el golpe lo mata."""
        self.vida -= 1
        self.flash = 8
        self.aturdido = 6 if self.es_jefe else 12
        self.kb_x = dirx * (2.5 if self.es_jefe else 7.0)
        if self.estado in ("telegrafia", "carga") and not self.es_jefe:
            self.estado = "patrulla"
        if self.vida <= 0:
            self.vivo = False
            return True
        return False

    def _suelo_delante(self, dirn, plataformas, suelo_y):
        px = int(self.x + (self.ancho + 3 if dirn > 0 else -3))
        py = int(self.y + self.alto + 4)
        if py >= suelo_y:
            return True
        for p in plataformas:
            if p.rect.collidepoint(px, py):
                return True
        return False

    # ---------------------------------------------------------------- IA
    def _ia_comun(self, dx, dy, plataformas, suelo_y):
        """Slime/hongo: patrullan sin caerse y persiguen si te ven en su mismo nivel."""
        if not self.en_suelo:
            return 0.0
        ve = abs(dx) <= self.vision and abs(dy) <= 70
        if ve:
            self.estado = "persigue"
            if abs(dx) > 8:
                self.direccion = 1 if dx > 0 else -1
            vel = self.vel_x * 1.5 if abs(dx) > 8 else 0.0
            if vel and not self._suelo_delante(self.direccion, plataformas, suelo_y):
                vel = 0.0  # al borde: se detiene en vez de caer
        else:
            self.estado = "patrulla"
            if not self._suelo_delante(self.direccion, plataformas, suelo_y):
                self.direccion *= -1
            vel = self.vel_x
        return vel * self.direccion

    def _ia_saltador(self, dx, salto_vel, cd_base, rango):
        """jefe1 / jefe_final: persigue y, tras avisar con un destello, salta hacia ti."""
        dirh = 1 if dx > 0 else -1
        self.cd -= 1
        if self.estado == "telegrafia":
            self.t_estado -= 1
            if self.t_estado <= 0:
                self.vel_y = salto_vel
                self.estado = "salto"
                self.t_estado = 14
                self.salto_dir = dirh
                self.direccion = dirh
            return 0.0
        if self.estado == "salto":
            self.t_estado -= 1
            if self.t_estado <= 0 and self.en_suelo:
                self.estado = "persigue"
                self.cd = int(cd_base / math.sqrt(self.dificultad))
            return 4.5 * self.salto_dir
        self.estado = "persigue"
        if abs(dx) > 6:
            self.direccion = dirh
        if self.cd <= 0 and abs(dx) < rango and self.en_suelo:
            self.estado = "telegrafia"
            self.t_estado = 25
            return 0.0
        return self.vel_x * (self.direccion if abs(dx) > 6 else 0)

    def _ia_embestida(self, dx):
        """jefe2 (gusano): se arrastra hacia ti y embiste en línea recta tras un aviso."""
        dirh = 1 if dx > 0 else -1
        self.cd -= 1
        if self.estado == "telegrafia":
            self.t_estado -= 1
            self.direccion = dirh
            if self.t_estado <= 0:
                self.estado = "carga"
                self.t_estado = 50
                self.salto_dir = dirh
            return 0.0
        if self.estado == "carga":
            self.t_estado -= 1
            if self.t_estado <= 0:
                self.estado = "persigue"
                self.cd = int(160 / math.sqrt(self.dificultad))
            return 7.5 * self.salto_dir
        self.estado = "persigue"
        if abs(dx) > 6:
            self.direccion = dirh
        if self.cd <= 0 and abs(dx) < 420:
            self.estado = "telegrafia"
            self.t_estado = 40
            return 0.0
        return self.vel_x * self.direccion

    def _ia_jefe(self, dx):
        if self.tipo == "jefe1":
            return self._ia_saltador(dx, -13, 150, 240)
        if self.tipo == "jefe2":
            return self._ia_embestida(dx)
        # jefe_final: más rápido y agresivo con la mitad de vida
        if self.vida <= self.vida_max // 2:
            self.vel_x = 4.2
            self.velocidad_anim = 0.25
        return self._ia_saltador(dx, -13.5, 110, 280)

    def _ia_volador(self, heroe_rect, ancho_pantalla, suelo_y):
        cx, cy = self.x + self.ancho / 2, self.y + self.alto / 2
        dx, dy = heroe_rect.centerx - cx, heroe_rect.centery - cy
        dist = math.hypot(dx, dy)
        if self.aturdido > 0:
            self.aturdido -= 1
            self.x += self.kb_x
            self.kb_x *= 0.8
        elif dist <= self.vision and dist > 1:
            self.estado = "persigue"
            v = self.vel_x * 1.25
            self.x += dx / dist * v
            self.y += dy / dist * v
            self.direccion = 1 if dx > 0 else -1
        else:
            self.estado = "patrulla"
            self.fase += 0.03
            tx = self.home_x + math.sin(self.fase) * 70
            ty = self.home_y + math.sin(self.fase * 2.3) * 14
            nx = self.x + (tx - self.x) * 0.06
            self.direccion = 1 if nx >= self.x else -1
            self.x = nx
            self.y += (ty - self.y) * 0.06
        self.x = max(0, min(self.x, ancho_pantalla - self.ancho))
        self.y = max(0, min(self.y, suelo_y - self.alto))

    # ---------------------------------------------------------------- actualización
    def actualizar(self, heroe_rect, plataformas, enemigos=None, suelo_y=510, ancho_pantalla=800):
        if not self.vivo:
            return
        self.indice_anim += self.velocidad_anim
        if self.indice_anim >= len(self.frames):
            self.indice_anim = 0.0
        if self.flash > 0:
            self.flash -= 1

        if self.volador:
            self._ia_volador(heroe_rect, ancho_pantalla, suelo_y)
            return

        dx = heroe_rect.centerx - (self.x + self.ancho / 2)
        dy = heroe_rect.bottom - (self.y + self.alto)
        if self.aturdido > 0:
            self.aturdido -= 1
            self.x += self.kb_x
            self.kb_x *= 0.8
        else:
            mov = self._ia_jefe(dx) if self.es_jefe else self._ia_comun(dx, dy, plataformas, suelo_y)
            self.x += mov

        # Bordes de pantalla
        if self.x < 0:
            self.x = 0.0
            self.direccion = 1
            if self.estado == "carga":
                self.t_estado = 0
        elif self.x > ancho_pantalla - self.ancho:
            self.x = float(ancho_pantalla - self.ancho)
            self.direccion = -1
            if self.estado == "carga":
                self.t_estado = 0

        # Gravedad + aterrizaje
        feet_previo = self.y + self.alto
        self.vel_y += self.gravedad
        self.y += self.vel_y
        self.en_suelo = False
        pies = self.y + self.alto
        if pies >= suelo_y:
            self.y = suelo_y - self.alto
            self.vel_y = 0.0
            self.en_suelo = True
        elif self.vel_y >= 0:
            r_e = self.rect
            for p in plataformas:
                r = p.rect
                if r_e.right > r.left and r_e.left < r.right and feet_previo <= r.top + 6 and pies >= r.top:
                    self.y = r.top - self.alto
                    self.vel_y = 0.0
                    self.en_suelo = True
                    break

        # Separación entre enemigos pequeños de suelo (evita que se apilen)
        if enemigos and not self.es_jefe:
            r_e = self.rect
            for otro in enemigos:
                if otro is not self and otro.vivo and not otro.es_jefe and not otro.volador \
                        and r_e.colliderect(otro.rect):
                    self.direccion = 1 if self.x >= otro.x else -1
                    self.x += self.direccion * 1.5
                    break

    # ---------------------------------------------------------------- dibujo
    def dibujar(self, superficie):
        if not self.vivo:
            return
        i = int(self.indice_anim) % len(self.frames)
        avisando = self.estado == "telegrafia" and (self.t_estado // 3) % 2 == 0
        izq = self.direccion == -1
        if self.flash > 0 or avisando:
            img = (self.blancos_flip if izq else self.blancos)[i]
        else:
            img = (self.frames_flip if izq else self.frames)[i]
        ox = random.choice((-2, 2)) if self.estado == "telegrafia" else 0
        superficie.blit(img, (int(self.x) + ox, int(self.y)))

        if self.estado == "telegrafia":  # signo de exclamación de advertencia
            ex, ey = int(self.x + self.ancho / 2), int(self.y) - 34
            pygame.draw.rect(superficie, (255, 60, 40), (ex - 3, ey, 6, 16))
            pygame.draw.rect(superficie, (255, 60, 40), (ex - 3, ey + 20, 6, 6))

        if self.es_jefe:
            ancho_barra = self.ancho + 10
            bx, by = int(self.x) - 5, int(self.y) - 15
            pygame.draw.rect(superficie, (80, 20, 20), (bx, by, ancho_barra, 6))
            fase2 = self.tipo == "jefe_final" and self.vida <= self.vida_max // 2
            color = (240, 200, 20) if fase2 else (50, 220, 90)
            pygame.draw.rect(superficie, color, (bx, by, int(ancho_barra * max(0, self.vida) / self.vida_max), 6))
