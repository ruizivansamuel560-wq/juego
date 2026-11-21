# -*- coding: utf-8 -*-
"""Knight Adventure - Metroidvania de plataformas (Pygame, compatible con pygbag)."""
import asyncio
import math
import os
import random

import pygame

import recursos
from jugador import Jugador, FRAME_MS
from nivel import Nivel, TOTAL_NIVELES
from particula import SistemaParticulas
from sonido import Sonidos

pygame.init()

ANCHO, ALTO = 800, 600
SUELO_Y = ALTO - 90
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Knight Adventure - Metroidvania Python")
reloj = pygame.time.Clock()

ruta_assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

TECLAS_SALTO = (pygame.K_SPACE, pygame.K_w, pygame.K_UP)
BANNER_FRAMES = 150
FRAMES_HASTA_GAMEOVER = 75


def _panel(ancho, alto, color=(10, 8, 20, 170)):
    s = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    pygame.draw.rect(s, color, (0, 0, ancho, alto), border_radius=10)
    pygame.draw.rect(s, (255, 255, 255, 40), (0, 0, ancho, alto), 2, border_radius=10)
    return s


class Juego:
    def __init__(self, superficie):
        self.pantalla = superficie
        self.lienzo = pygame.Surface((ANCHO, ALTO))
        self.corriendo = True

        # ---------------- Recursos ----------------
        r = recursos.obtener(ruta_assets)
        fondo = pygame.transform.scale(r.imagen("background.png"), (ANCHO, ALTO))
        tileset = r.imagen("tileset_32x32(new).png")
        self.textura_suelo = tileset.subsurface(pygame.Rect(0, 0, 32, 32))
        # Fondo + suelo se pre-renderizan UNA vez (antes se escalaba la textura cada frame)
        self.fondo = fondo.copy()
        bloque = pygame.transform.scale(self.textura_suelo, (40, 40))
        for fila in range(3):
            for x in range(0, ANCHO, 40):
                self.fondo.blit(bloque, (x, SUELO_Y + fila * 40))
        self.img_corazon = pygame.transform.scale(r.imagen("hearts_hud.png"), (30, 30))
        self.img_corazon_vacio = pygame.transform.scale(r.imagen("no_hearts_hud.png"), (30, 30))
        self.img_moneda = pygame.transform.scale(r.imagen("coins_hud.png"), (24, 24))
        puerta = pygame.transform.scale(r.imagen("door.png"), (56, 56))
        self.puerta_abierta = puerta
        self.puerta_cerrada = puerta.copy()
        self.puerta_cerrada.fill((80, 80, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)

        # ---------------- UI pre-renderizada ----------------
        self._fuentes = {}
        self._cache_txt = {}
        self.filtro_menu = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.filtro_menu.fill((15, 10, 25, 175))
        self.filtro_pausa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.filtro_pausa.fill((0, 0, 0, 150))
        self.filtro_go = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.filtro_go.fill((90, 0, 0, 175))
        self.filtro_win = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.filtro_win.fill((0, 35, 20, 150))
        self.panel_izq = _panel(224, 108)
        self.panel_der = _panel(196, 66)
        self.panel_controles = _panel(620, 84)
        self.boton_jugar = pygame.Rect(ANCHO // 2 - 130, 372, 260, 56)

        # ---------------- Estado ----------------
        self.estado = "menu"      # menu | jugando | pausa | gameover | victoria
        self.sonidos = None       # se crea tras el primer gesto del usuario (política de audio del navegador)
        self.particulas = SistemaParticulas()
        self.t_menu = 0
        self.reiniciar_partida()
        self.menu_heroe = [pygame.transform.scale(f, (f.get_width() * 2, f.get_height() * 2))
                           for f in self.heroe.anim_idle]

    # ------------------------------------------------------------------ utilidades
    def sfx(self, nombre):
        if self.sonidos:
            self.sonidos.play(nombre)

    def fuente(self, tam):
        f = self._fuentes.get(tam)
        if f is None:
            f = self._fuentes[tam] = pygame.font.Font(None, tam)
        return f

    def texto(self, txt, tam, color, sombra=True):
        clave = (txt, tam, color, sombra)
        s = self._cache_txt.get(clave)
        if s is None:
            if len(self._cache_txt) > 300:
                self._cache_txt.clear()
            base = self.fuente(tam).render(txt, True, color)
            if sombra:
                sh = self.fuente(tam).render(txt, True, (0, 0, 0))
                s = pygame.Surface((base.get_width() + 2, base.get_height() + 2), pygame.SRCALPHA)
                s.blit(sh, (2, 2))
                s.blit(base, (0, 0))
            else:
                s = base
            self._cache_txt[clave] = s
        return s

    def dibujar_texto(self, sup, txt, tam, color, centro=None, izq=None, alpha=None):
        s = self.texto(txt, tam, color)
        if alpha is not None:
            s = s.copy()
            s.set_alpha(alpha)
        if centro is not None:
            sup.blit(s, s.get_rect(center=centro))
        else:
            sup.blit(s, izq)

    def agitar(self, magnitud):
        self.shake = max(self.shake, magnitud)

    # ------------------------------------------------------------------ flujo de partida
    def reiniciar_partida(self):
        self.heroe = Jugador(50, 400, ruta_assets)
        self.puntos = 0
        self.monedas = 0
        self.nivel_actual = 1
        self.mapa = Nivel(1, self.textura_suelo, ruta_assets)
        self.particulas.limpiar()
        self.reloj_juego = 0.0
        self.hitstop = 0.0
        self.shake = 0.0
        self.banner = BANNER_FRAMES
        self.aviso_salida = 0
        self.timer_muerte = 0
        self.frame = 0

    def iniciar_partida(self):
        self.reiniciar_partida()
        self.estado = "jugando"
        self.sfx("menu")

    def ir_a_nivel(self, n):
        self.nivel_actual = n
        self.mapa = Nivel(n, self.textura_suelo, ruta_assets)
        self.heroe.x = 40.0
        self.heroe.dar_invulnerabilidad(1000)
        self.particulas.limpiar()
        self.banner = BANNER_FRAMES
        self.puntos += 250
        self.sfx("nivel")

    # ------------------------------------------------------------------ entrada
    def procesar_eventos(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.corriendo = False  # en la web este evento no se dispara
                continue
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and self.sonidos is None:
                self.sonidos = Sonidos()
            if ev.type == pygame.KEYDOWN:
                self.tecla(ev.key)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.estado == "menu" and self.boton_jugar.collidepoint(ev.pos):
                    self.iniciar_partida()

    def tecla(self, k):
        e = self.estado
        if e == "menu":
            if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.iniciar_partida()
        elif e == "jugando":
            h = self.heroe
            if k in (pygame.K_ESCAPE, pygame.K_p) and not h.muerto:
                self.estado = "pausa"
            elif h.muerto:
                if k == pygame.K_r:                       # reinicio instantáneo
                    self.iniciar_partida()
            elif k in TECLAS_SALTO:
                h.pulsar_salto()
            elif k in (pygame.K_k, pygame.K_j):
                h.atacar()
            elif k in (pygame.K_l, pygame.K_LSHIFT, pygame.K_RSHIFT):
                h.iniciar_dash()
        elif e == "pausa":
            if k in (pygame.K_ESCAPE, pygame.K_p):
                self.estado = "jugando"
            elif k == pygame.K_r:
                self.iniciar_partida()
            elif k == pygame.K_m:
                self.reiniciar_partida()
                self.estado = "menu"
        elif e in ("gameover", "victoria"):
            if k in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.iniciar_partida()
            elif k in (pygame.K_m, pygame.K_ESCAPE):
                self.reiniciar_partida()
                self.estado = "menu"

    # ------------------------------------------------------------------ lógica
    def actualizar(self):
        self.shake *= 0.86
        if self.shake < 0.3:
            self.shake = 0.0

        e = self.estado
        if e == "menu":
            self.t_menu += 1
            return
        if e == "pausa":
            return
        if e == "gameover":
            self.particulas.actualizar()
            return
        if e == "victoria":
            self.particulas.confeti(ANCHO)
            self.particulas.actualizar()
            return

        # ----- jugando -----
        if self.hitstop > 0:           # Hitstop: micro-pausa de impacto
            self.hitstop -= FRAME_MS
            return

        self.frame += 1
        self.reloj_juego += FRAME_MS
        mapa, h = self.mapa, self.heroe
        mapa.actualizar(self.reloj_juego)
        teclas = pygame.key.get_pressed()
        h.actualizar(teclas, mapa.plataformas, mapa.enemigos, SUELO_Y, ANCHO)

        for en in mapa.enemigos:
            if en.vivo:
                en.actualizar(h.rect, mapa.plataformas, mapa.enemigos, SUELO_Y, ANCHO)

        if not h.muerto:
            rh = h.rect
            for o in mapa.objetos:
                if not o.activo or not rh.colliderect(o.rect):
                    continue
                if o.tipo == "moneda":
                    o.activo = False
                    self.monedas += 1
                    self.puntos += 100
                    self.particulas.moneda(o.x + o.ancho / 2, o.y + o.alto / 2)
                    self.sfx("moneda")
                elif o.tipo == "pocion":
                    if h.curar():
                        o.activo = False
                        self.puntos += 50
                        self.particulas.moneda(o.x + o.ancho / 2, o.y + o.alto / 2)
                        self.sfx("moneda")
                elif o.peligroso:
                    h.recibir_danio(o.x + o.ancho / 2)
            for en in mapa.enemigos:
                if en.vivo and rh.colliderect(en.rect):
                    h.recibir_danio(en.x + en.ancho / 2)

            # Salida por el borde derecho
            if h.rect.right >= ANCHO - 1:
                if mapa.salida_abierta:
                    if self.nivel_actual < TOTAL_NIVELES:
                        self.ir_a_nivel(self.nivel_actual + 1)
                    else:
                        self.estado = "victoria"
                        self.puntos += 1000
                        self.particulas.limpiar()
                        self.sfx("victoria")
                else:
                    self.aviso_salida = 100
        else:
            self.timer_muerte += 1
            if self.timer_muerte >= FRAMES_HASTA_GAMEOVER:
                self.estado = "gameover"
                self.sfx("gameover")

        self._procesar_eventos_heroe()
        self.particulas.actualizar()
        if self.banner > 0:
            self.banner -= 1
        if self.aviso_salida > 0:
            self.aviso_salida -= 1

    def _procesar_eventos_heroe(self):
        h = self.heroe
        for ev in h.eventos:
            t = ev[0]
            if t == "salto":
                self.particulas.salto(ev[1], ev[2])
                self.sfx("salto")
            elif t == "aterrizaje":
                self.particulas.aterrizaje(ev[1], ev[2], ev[3])
                if ev[3] > 0.6:
                    self.sfx("aterrizaje")
            elif t == "golpe":
                _, x, y, mato, jefe, _en = ev
                self.particulas.impacto(x, y)
                self.sfx("golpe")
                self.hitstop = max(self.hitstop, 50 if mato else 40)
                self.agitar(4)
                if mato:
                    self.particulas.muerte_enemigo(x, y, jefe)
                    self.sfx("muerte_enemigo")
                    self.puntos += 500 if jefe else 50
                    self.agitar(11 if jefe else 7)
            elif t == "danio":
                self.particulas.danio(ev[1], ev[2])
                self.sfx("danio")
                self.hitstop = max(self.hitstop, 50)
                self.agitar(9)
            elif t == "muerte":
                self.agitar(13)
            elif t == "dash":
                self.sfx("dash")
            elif t == "dash_estela":
                self.particulas.dash(ev[1], ev[2])
        h.eventos.clear()

    # ------------------------------------------------------------------ dibujo
    def dibujar(self):
        L = self.lienzo
        if self.estado == "menu":
            self.dibujar_menu(L)
        else:
            self.dibujar_mundo(L)
            self.dibujar_hud(L)
            if self.estado == "pausa":
                self.dibujar_pausa(L)
            elif self.estado == "gameover":
                self.dibujar_gameover(L)
            elif self.estado == "victoria":
                self.dibujar_victoria(L)

        # Screen shake: se desplaza el lienzo completo
        self.pantalla.fill((12, 10, 20))
        if self.shake > 0:
            ox = int(random.uniform(-self.shake, self.shake))
            oy = int(random.uniform(-self.shake, self.shake))
        else:
            ox = oy = 0
        self.pantalla.blit(L, (ox, oy))

    def dibujar_mundo(self, L):
        L.blit(self.fondo, (0, 0))
        mapa = self.mapa
        L.blit(self.puerta_abierta if mapa.salida_abierta else self.puerta_cerrada, (ANCHO - 62, SUELO_Y - 56))
        for p in mapa.plataformas:
            p.dibujar(L)
        for o in mapa.objetos:
            o.dibujar(L)
        for en in mapa.enemigos:
            en.dibujar(L)
        self.heroe.dibujar(L)
        self.particulas.dibujar(L)

    def dibujar_hud(self, L):
        h = self.heroe
        L.blit(self.panel_izq, (10, 10))
        for i in range(h.vida_max):
            L.blit(self.img_corazon if i < h.vida else self.img_corazon_vacio, (20 + i * 34, 17))
        L.blit(self.img_moneda, (20, 54))
        self.dibujar_texto(L, "x %d" % self.monedas, 30, (255, 215, 0), izq=(52, 56))
        self.dibujar_texto(L, "PUNTOS %06d" % self.puntos, 24, (255, 255, 255), izq=(20, 84))

        L.blit(self.panel_der, (ANCHO - 206, 10))
        self.dibujar_texto(L, "NIVEL %d/%d" % (self.nivel_actual, TOTAL_NIVELES), 32, (255, 255, 255),
                           centro=(ANCHO - 108, 30))
        self.dibujar_texto(L, self.mapa.nombre, 22, (0, 238, 255), centro=(ANCHO - 108, 54))

        # Barra de jefe (arriba al centro)
        for en in self.mapa.enemigos:
            if en.vivo and en.es_jefe:
                bx, by, bw = 290, 20, 220
                pygame.draw.rect(L, (60, 15, 15), (bx, by, bw, 14), border_radius=4)
                pygame.draw.rect(L, (230, 60, 60), (bx, by, int(bw * en.vida / en.vida_max), 14), border_radius=4)
                pygame.draw.rect(L, (255, 255, 255), (bx, by, bw, 14), 2, border_radius=4)
                self.dibujar_texto(L, "JEFE", 22, (255, 255, 255), centro=(ANCHO // 2, 42))
                break

        if self.banner > 0 and self.estado == "jugando":
            a = min(255, self.banner * 5)
            self.dibujar_texto(L, "NIVEL %d" % self.nivel_actual, 72, (255, 255, 255), centro=(ANCHO // 2, 170), alpha=a)
            self.dibujar_texto(L, self.mapa.nombre, 34, (0, 238, 255), centro=(ANCHO // 2, 214), alpha=a)
        if self.aviso_salida > 0 and (self.aviso_salida // 8) % 2 == 0:
            self.dibujar_texto(L, "¡Derrota al jefe para abrir la puerta!", 34, (255, 120, 90),
                               centro=(ANCHO // 2, 110))

    def dibujar_menu(self, L):
        L.blit(self.fondo, (0, 0))
        L.blit(self.filtro_menu, (0, 0))
        t = self.t_menu
        bob = math.sin(t * 0.05) * 6
        self.dibujar_texto(L, "KNIGHT ADVENTURE", 92, (0, 238, 255), centro=(ANCHO // 2, 105 + bob))
        self.dibujar_texto(L, "Metroidvania de plataformas  -  %d niveles" % TOTAL_NIVELES, 28, (190, 190, 210),
                           centro=(ANCHO // 2, 165))
        fr = self.menu_heroe[(t // 9) % len(self.menu_heroe)]
        L.blit(fr, fr.get_rect(midbottom=(ANCHO // 2, 350)))

        hover = self.boton_jugar.collidepoint(pygame.mouse.get_pos())
        color = (0, 190, 210) if hover else (0, 130, 160)
        pygame.draw.rect(L, color, self.boton_jugar, border_radius=12)
        pygame.draw.rect(L, (255, 255, 255), self.boton_jugar, 3, border_radius=12)
        self.dibujar_texto(L, "JUGAR", 46, (255, 255, 255), centro=self.boton_jugar.center)
        if (t // 30) % 2 == 0:
            self.dibujar_texto(L, "o pulsa ESPACIO / ENTER", 26, (230, 230, 240), centro=(ANCHO // 2, 452))

        L.blit(self.panel_controles, (90, 488))
        self.dibujar_texto(L, "A/D o Flechas: Mover   |   ESPACIO / W / Arriba: Saltar (mantén = más alto)", 22,
                           (210, 210, 220), centro=(ANCHO // 2, 512))
        self.dibujar_texto(L, "K o J: Atacar   |   L o SHIFT: Dash   |   ESC o P: Pausa", 22,
                           (210, 210, 220), centro=(ANCHO // 2, 540))

    def dibujar_pausa(self, L):
        L.blit(self.filtro_pausa, (0, 0))
        self.dibujar_texto(L, "PAUSA", 100, (255, 255, 255), centro=(ANCHO // 2, 220))
        self.dibujar_texto(L, "ESC / P: Continuar", 32, (0, 238, 255), centro=(ANCHO // 2, 320))
        self.dibujar_texto(L, "R: Reiniciar partida", 32, (230, 230, 230), centro=(ANCHO // 2, 360))
        self.dibujar_texto(L, "M: Menú principal", 32, (230, 230, 230), centro=(ANCHO // 2, 400))

    def dibujar_gameover(self, L):
        L.blit(self.filtro_go, (0, 0))
        self.dibujar_texto(L, "GAME OVER", 110, (255, 60, 60), centro=(ANCHO // 2, 210))
        self.dibujar_texto(L, "Puntos: %d   |   Monedas: %d   |   Nivel: %d" %
                           (self.puntos, self.monedas, self.nivel_actual), 32, (255, 255, 255),
                           centro=(ANCHO // 2, 300))
        if (pygame.time.get_ticks() // 450) % 2 == 0:
            self.dibujar_texto(L, "Pulsa R para volver a intentarlo", 38, (255, 230, 120), centro=(ANCHO // 2, 380))
        self.dibujar_texto(L, "M: Menú principal", 26, (210, 210, 210), centro=(ANCHO // 2, 430))

    def dibujar_victoria(self, L):
        L.blit(self.filtro_win, (0, 0))
        self.particulas.dibujar(L)
        self.dibujar_texto(L, "¡CAMPEÓN DEFINITIVO!", 84, (90, 255, 140), centro=(ANCHO // 2, 190))
        self.dibujar_texto(L, "Has derrotado al jefe final", 34, (255, 255, 255), centro=(ANCHO // 2, 255))
        self.dibujar_texto(L, "Puntos: %d   |   Monedas: %d" % (self.puntos, self.monedas), 40, (255, 215, 0),
                           centro=(ANCHO // 2, 320))
        if (pygame.time.get_ticks() // 450) % 2 == 0:
            self.dibujar_texto(L, "R / ENTER: Jugar de nuevo", 34, (255, 255, 255), centro=(ANCHO // 2, 400))
        self.dibujar_texto(L, "M: Menú principal", 26, (210, 210, 210), centro=(ANCHO // 2, 445))


async def main():
    # Si falta un asset se muestra el error en pantalla (sin sys.exit / pygame.quit: congelarían la pestaña web)
    try:
        juego = Juego(pantalla)
    except Exception as exc:
        mensaje = "Error cargando recursos: %s" % exc
        fuente = pygame.font.Font(None, 28)
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return
            pantalla.fill((30, 0, 0))
            pantalla.blit(fuente.render(mensaje[:90], True, (255, 200, 200)), (20, ALTO // 2 - 10))
            pygame.display.flip()
            reloj.tick(30)
            await asyncio.sleep(0)

    while juego.corriendo:
        juego.procesar_eventos()
        juego.actualizar()
        juego.dibujar()
        pygame.display.flip()
        reloj.tick(60)
        await asyncio.sleep(0)  # imprescindible en pygbag: cede el control al navegador


asyncio.run(main())
