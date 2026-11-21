# -*- coding: utf-8 -*-
"""Carga de assets con índice único (un solo os.walk) y caché de imágenes/frames.
Antes cada Jugador/Enemigo/Objeto recorría TODA la carpeta assets al crearse;
en la web eso era lento. Ahora se indexa una sola vez."""
import os

import pygame

_instancia = None


class Recursos:
    def __init__(self, ruta_assets):
        self.ruta_assets = ruta_assets
        self.indice = {}
        for carpeta, _subs, archivos in os.walk(ruta_assets):
            for nombre in archivos:
                self.indice.setdefault(nombre, os.path.join(carpeta, nombre))
        self._imagenes = {}
        self._frames = {}
        self._blancos = {}

    def ruta(self, nombre):
        return self.indice.get(nombre)

    def imagen(self, nombre):
        img = self._imagenes.get(nombre)
        if img is None:
            ruta = self.indice.get(nombre)
            if not ruta:
                raise FileNotFoundError("No se encontró el asset: " + nombre)
            img = pygame.image.load(ruta).convert_alpha()
            self._imagenes[nombre] = img
        return img

    def frames(self, nombre, cantidad, escala=None, tam=None):
        """Corta una tira horizontal en `cantidad` cuadros y los escala."""
        clave = (nombre, cantidad, escala, tam)
        res = self._frames.get(clave)
        if res is None:
            tira = self.imagen(nombre)
            fw = tira.get_width() // cantidad
            fh = tira.get_height()
            if tam is None:
                tam = (int(fw * (escala or 1)), int(fh * (escala or 1)))
            res = []
            for i in range(cantidad):
                cuadro = tira.subsurface(pygame.Rect(i * fw, 0, fw, fh))
                res.append(pygame.transform.scale(cuadro, tam))
            self._frames[clave] = res
        return res

    @staticmethod
    def siluetas_blancas(frames):
        """Versión totalmente blanca de cada frame (efecto de destello al recibir golpe)."""
        res = []
        for f in frames:
            try:
                m = pygame.mask.from_surface(f)
                res.append(m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)))
            except Exception:
                res.append(f)
        return res


def obtener(ruta_assets):
    global _instancia
    if _instancia is None or _instancia.ruta_assets != ruta_assets:
        _instancia = Recursos(ruta_assets)
    return _instancia
