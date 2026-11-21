# -*- coding: utf-8 -*-
import pygame

import recursos

FRAME_MS = 1000.0 / 60.0  # el juego simula a paso fijo de 60 FPS


class Jugador:
    # --- Game feel (ms) ---
    COYOTE_MS = 110    # margen para saltar tras dejar una plataforma
    BUFFER_MS = 120    # el salto pulsado justo antes de aterrizar se recuerda

    def __init__(self, x, y, ruta_assets):
        self.x = float(x)
        self.y = float(y)
        self.vel_x = 5
        self.vel_y = 0.0
        self.gravedad = 0.65
        self.fuerza_salto = -14.5
        self.vel_caida_max = 15
        self.en_el_suelo = False
        self.plataforma_suelo = None
        self.mirando_derecha = True

        self.t = 0.0                    # reloj interno (ms de juego; se congela en pausa/hitstop)
        self.t_ultimo_suelo = -1e9
        self.t_salto_pedido = -1e9
        self.salto_mantenido = False

        self.vida_max = 3
        self.vida = 3
        self.muerto = False
        self.invulnerable = False
        self.t_fin_invulnerable = 0.0
        self.duracion_invulnerable = 1500
        self.t_herido = -1e9
        self.kb_x = 0.0

        self.puede_dash = True
        self.en_dash = False
        self.t_dash = 0.0
        self.duracion_dash = 200
        self.vel_dash = 15
        self.direccion_dash = 1
        self._pasos_dash = 0

        self.estado = "quieto"
        self.indice_anim = 0.0
        self.velocidad_anim = 0.15
        self.golpeados = set()
        self.eventos = []               # main los consume: ("salto", x, y) ...

        self._cargar_graficos(ruta_assets)
        self.imagen_actual = self.anim_idle[0]

        # Hitbox más pequeña que el sprite: evita atascos y "golpes fantasma"
        self.inset_x = 8
        self.inset_top = 4

    # ------------------------------------------------------------------ gráficos
    def _cargar_graficos(self, ruta_assets):
        r = recursos.obtener(ruta_assets)
        m = 3.2
        self.anim_idle = r.frames("herochar_idle_anim_strip_4.png", 4, escala=m)
        self.ancho, self.alto = self.anim_idle[0].get_size()
        self.anim_run = r.frames("herochar_run_anim_strip_6.png", 6, escala=m)
        self.anim_attack = r.frames("herochar_sword_attack_anim_strip_4.png", 4, escala=m)
        self.anim_efecto_espada = r.frames("sword_effect_strip_4(new).png", 4, escala=4.0)
        # Animaciones extra (existen en el asset pack)
        self.anim_salto = r.frames("herochar_jump_up_anim_strip_3.png", 3, escala=m)
        self.anim_caida = r.frames("herochar_jump_down_anim_strip_3.png", 3, escala=m)
        self.anim_herido = r.frames("herochar_hit_anim_strip_3.png", 3, escala=m)
        self.anim_muerte = r.frames("herochar_death_anim_strip_8.png", 8, escala=m)

    @property
    def rect(self):
        """Hitbox real del jugador (para daño, objetos y plataformas)."""
        return pygame.Rect(int(self.x) + self.inset_x, int(self.y) + self.inset_top,
                           self.ancho - 2 * self.inset_x, self.alto - self.inset_top)

    # ------------------------------------------------------------------ acciones
    def pulsar_salto(self):
        """Llamar en KEYDOWN: alimenta el Jump Buffer."""
        self.t_salto_pedido = self.t

    def atacar(self):
        if self.muerto or self.estado == "atacando" or self.en_dash:
            return False
        self.estado = "atacando"
        self.indice_anim = 0.0
        self.golpeados = set()
        return True

    def iniciar_dash(self):
        if self.muerto or not self.puede_dash or self.en_dash or self.estado == "atacando":
            return False
        self.en_dash = True
        self.puede_dash = False
        self.t_dash = self.t
        self.direccion_dash = 1 if self.mirando_derecha else -1
        self.vel_y = 0
        self.eventos.append(("dash", self.x + self.ancho / 2, self.y + self.alto))
        return True

    def recibir_danio(self, origen_x=None):
        if self.invulnerable or self.en_dash or self.muerto:
            return False
        self.vida = max(0, self.vida - 1)
        self.invulnerable = True
        self.t_fin_invulnerable = self.t + self.duracion_invulnerable
        self.t_herido = self.t
        self.vel_y = -7
        centro = self.x + self.ancho / 2
        if origen_x is None:
            lejos = -1 if self.mirando_derecha else 1
        else:
            lejos = 1 if centro >= origen_x else -1
        self.kb_x = 9.0 * lejos      # empujón suave con decaimiento (no teletransporte)
        self.en_dash = False
        self.estado = "quieto" if self.estado == "atacando" else self.estado
        self.eventos.append(("danio", centro, self.y + self.alto / 2))
        if self.vida <= 0:
            self.muerto = True
            self.estado = "muerto"
            self.indice_anim = 0.0
            self.eventos.append(("muerte", centro, self.y + self.alto / 2))
        return True

    def curar(self, cantidad=1):
        if self.vida >= self.vida_max or self.muerto:
            return False
        self.vida = min(self.vida_max, self.vida + cantidad)
        return True

    def dar_invulnerabilidad(self, ms):
        self.invulnerable = True
        self.t_fin_invulnerable = max(self.t_fin_invulnerable, self.t + ms)

    # ------------------------------------------------------------------ física
    def _hitbox_ataque(self):
        rango, alto = 95, self.alto + 30
        if self.mirando_derecha:
            return pygame.Rect(int(self.x) + self.ancho - 10, int(self.y) - 15, rango, alto)
        return pygame.Rect(int(self.x) - rango + 10, int(self.y) - 15, rango, alto)

    def _resolver_ataque(self, enemigos):
        # La espada sólo hace daño en los cuadros 1-2 de la animación (se siente más real)
        if not enemigos or int(self.indice_anim) not in (1, 2):
            return
        caja = self._hitbox_ataque()
        dirx = 1 if self.mirando_derecha else -1
        for e in enemigos:
            if e.vivo and e not in self.golpeados and caja.colliderect(e.rect):
                self.golpeados.add(e)
                mato = e.recibir_golpe(dirx)
                self.eventos.append(("golpe", e.x + e.ancho / 2, e.y + e.alto / 2, mato, e.es_jefe, e))

    def actualizar(self, teclas, plataformas, enemigos=None, suelo_y=510, ancho_pantalla=800):
        self.t += FRAME_MS
        if self.invulnerable and self.t >= self.t_fin_invulnerable:
            self.invulnerable = False

        self.salto_mantenido = bool(teclas[pygame.K_SPACE] or teclas[pygame.K_w] or teclas[pygame.K_UP])
        feet_previo = self.y + self.alto
        vel_y_previa = self.vel_y
        estaba_en_suelo = self.en_el_suelo

        # La plataforma móvil nos arrastra
        if self.en_el_suelo and self.plataforma_suelo is not None:
            self.x += self.plataforma_suelo.dx

        if self.muerto:
            self.kb_x *= 0.9
            self.x += self.kb_x
            self.vel_y = min(self.vel_y + self.gravedad, self.vel_caida_max)
            self.y += self.vel_y
            self.indice_anim = min(self.indice_anim + 0.16, len(self.anim_muerte) - 0.01)
            self.imagen_actual = self.anim_muerte[int(self.indice_anim)]
        elif self.en_dash:
            if self.t - self.t_dash > self.duracion_dash:
                self.en_dash = False
                self.vel_y = 0
            else:
                self.x += self.vel_dash * self.direccion_dash
                self.imagen_actual = self.anim_run[int(self.t / 50) % len(self.anim_run)]
                self._pasos_dash += 1
                if self._pasos_dash % 2 == 0:
                    self.eventos.append(("dash_estela", self.x + self.ancho / 2, self.y + self.alto / 2))
        else:
            mov = 0
            if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
                mov -= 1
            if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
                mov += 1
            atacando = self.estado == "atacando"
            if mov and not atacando:
                self.mirando_derecha = mov > 0
            self.x += mov * self.vel_x * (0.55 if atacando else 1.0)

            # Retroceso por daño
            if abs(self.kb_x) > 0.3:
                self.x += self.kb_x
                self.kb_x *= 0.82
            else:
                self.kb_x = 0.0

            # Gravedad variable: salto corto si sueltas la tecla, caída más ágil
            g = self.gravedad
            if self.vel_y < 0 and not self.salto_mantenido:
                g *= 2.4
            elif self.vel_y > 0:
                g *= 1.2
            self.vel_y = min(self.vel_y + g, self.vel_caida_max)
            self.y += self.vel_y

            # Estado / animación
            self.indice_anim += self.velocidad_anim
            if atacando:
                self.indice_anim += 0.07  # ataque más rápido
                if int(self.indice_anim) >= len(self.anim_attack):
                    self.estado = "quieto"
                    self.indice_anim = 0.0
                    atacando = False
                else:
                    self.imagen_actual = self.anim_attack[int(self.indice_anim)]
                    self._resolver_ataque(enemigos)
            if not atacando:
                if self.t - self.t_herido < 280:
                    self.estado = "herido"
                    self.imagen_actual = self.anim_herido[min(2, int((self.t - self.t_herido) / 95))]
                elif not self.en_el_suelo:
                    if self.vel_y < 0:
                        self.estado = "salto"
                        idx = 0 if self.vel_y < -8 else (1 if self.vel_y < -3 else 2)
                        self.imagen_actual = self.anim_salto[idx]
                    else:
                        self.estado = "caida"
                        idx = 0 if self.vel_y < 3 else (1 if self.vel_y < 8 else 2)
                        self.imagen_actual = self.anim_caida[idx]
                elif mov:
                    self.estado = "corriendo"
                    self.imagen_actual = self.anim_run[int(self.indice_anim) % len(self.anim_run)]
                else:
                    self.estado = "quieto"
                    self.imagen_actual = self.anim_idle[int(self.indice_anim) % len(self.anim_idle)]

        # Límites de pantalla (la hitbox puede tocar el borde exacto)
        self.x = max(-self.inset_x, min(self.x, ancho_pantalla - self.ancho + self.inset_x))

        # ---------------- Colisión vertical (suelo + plataformas de un sentido) ----------------
        self.en_el_suelo = False
        self.plataforma_suelo = None
        if self.vel_y >= 0:
            pies = self.y + self.alto
            if pies >= suelo_y:
                self.y = suelo_y - self.alto
                self.vel_y = 0
                self.en_el_suelo = True
            else:
                hb = self.rect
                # +4 px de tolerancia lateral: puedes aterrizar justo en la esquina de una plataforma
                izq, der = hb.left - 4, hb.right + 4
                for plat in plataformas:
                    r = plat.rect
                    if der > r.left and izq < r.right and feet_previo <= r.top + 6 and pies >= r.top:
                        self.y = r.top - self.alto
                        self.vel_y = 0
                        self.en_el_suelo = True
                        self.plataforma_suelo = plat
                        break

        if self.en_el_suelo:
            self.t_ultimo_suelo = self.t
            self.puede_dash = True
            if not estaba_en_suelo and vel_y_previa > 2:
                self.eventos.append(("aterrizaje", self.x + self.ancho / 2, self.y + self.alto,
                                     min(1.5, vel_y_previa / 12.0)))

        # ---------------- Salto con Coyote Time + Jump Buffer ----------------
        if (not self.muerto and not self.en_dash
                and self.t - self.t_salto_pedido <= self.BUFFER_MS
                and self.t - self.t_ultimo_suelo <= self.COYOTE_MS):
            self.vel_y = self.fuerza_salto
            self.t_salto_pedido = -1e9
            self.t_ultimo_suelo = -1e9
            self.en_el_suelo = False
            self.plataforma_suelo = None
            self.eventos.append(("salto", self.x + self.ancho / 2, self.y + self.alto))

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, superficie):
        if self.invulnerable and not self.muerto and int(self.t / 80) % 2 == 0:
            return  # parpadeo durante la invulnerabilidad
        img = self.imagen_actual
        x, y = int(self.x), int(self.y)
        extra = img.get_width() - self.ancho  # el cuadro de ataque es más ancho que el normal
        if self.mirando_derecha:
            superficie.blit(img, (x, y))
        else:
            superficie.blit(pygame.transform.flip(img, True, False), (x - extra, y))
        if self.estado == "atacando":
            fx = self.anim_efecto_espada[min(int(self.indice_anim), len(self.anim_efecto_espada) - 1)]
            if self.mirando_derecha:
                superficie.blit(fx, (x + 30, y - 10))
            else:
                superficie.blit(pygame.transform.flip(fx, True, False), (x - 45, y - 10))
