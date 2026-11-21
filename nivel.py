# -*- coding: utf-8 -*-
"""Niveles definidos como DATOS. Para añadir un nivel basta con agregar un diccionario a NIVELES.

Coordenadas en píxeles (pantalla 800x600, suelo en y=510).
  plataformas : (x, y, ancho)
  moviles     : (x, y, ancho, rango, velocidad)
  enemigos    : (x, y, tipo)           tipo: slime | hongo | mosca | jefe1 | jefe2 | jefe_final
  monedas     : (x, y)
  picos       : (x, y)                 picos fijos
  picos_ciclo : (x, y, desfase_ms)     trampa intermitente (avisa antes de salir)
  pociones    : (x, y)                 curan 1 corazón
Los niveles con jefe bloquean la salida hasta derrotarlo.
"""
from enemigo import Enemigo
from objeto import Objeto
from plataforma import Plataforma, PlataformaMovil

ALTO_PLAT = 35

NIVELES = [
    {   # 1 - tutorial: pocos enemigos, un solo pico
        "nombre": "Bosque tranquilo", "dificultad": 1.0,
        "plataformas": [(200, 410, 200), (480, 310, 200)],
        "moviles": [],
        "enemigos": [(260, 360, "slime"), (550, 250, "hongo"), (380, 470, "slime")],
        "monedas": [(260, 360), (330, 360), (540, 260), (610, 260), (700, 470)],
        "picos": [(600, 480)],
        "picos_ciclo": [],
        "pociones": [],
    },
    {   # 2 - escalera de plataformas, primera trampa intermitente
        "nombre": "Cuevas de piedra", "dificultad": 1.2,
        "plataformas": [(80, 410, 140), (280, 320, 140), (480, 230, 140), (650, 340, 120)],
        "moviles": [],
        "enemigos": [(110, 360, "hongo"), (300, 270, "slime"), (510, 180, "hongo"),
                     (200, 470, "slime"), (600, 470, "slime")],
        "monedas": [(130, 360), (330, 270), (530, 180), (690, 290), (420, 470), (250, 470)],
        "picos": [(330, 480), (370, 480)],
        "picos_ciclo": [(520, 480, 0)],
        "pociones": [(560, 200)],
    },
    {   # 3 - JEFE 1 (goblin saltarín), plataforma móvil sobre trampas, moscas
        "nombre": "Guarida del Goblin", "dificultad": 1.4,
        "plataformas": [(60, 400, 150), (300, 290, 150), (540, 380, 140)],
        "moviles": [(330, 430, 90, 100, 1.4)],
        "enemigos": [(80, 350, "slime"), (320, 240, "hongo"), (500, 200, "mosca"),
                     (650, 400, "jefe1")],
        "monedas": [(110, 350), (350, 240), (420, 400), (590, 330), (200, 470)],
        "picos": [(200, 480)],
        "picos_ciclo": [(320, 480, 0), (360, 480, 400), (400, 480, 800)],
        "pociones": [(340, 260)],
    },
    {   # 4 - JEFE 2 (gusano que embiste), mucha trampa de suelo y moscas
        "nombre": "Pantano maldito", "dificultad": 1.6,
        "plataformas": [(40, 400, 120), (200, 310, 120), (380, 230, 120)],
        "moviles": [(560, 330, 100, 110, 1.8)],
        "enemigos": [(60, 350, "hongo"), (220, 260, "slime"), (400, 150, "mosca"),
                     (620, 230, "mosca"), (620, 460, "jefe2")],
        "monedas": [(80, 350), (240, 260), (420, 180), (600, 280), (330, 470)],
        "picos": [(260, 480), (300, 480), (340, 480)],
        "picos_ciclo": [(470, 480, 0), (510, 480, 500)],
        "pociones": [(420, 200)],
    },
    {   # 5 - JEFE FINAL: todo junto
        "nombre": "Fortaleza final", "dificultad": 1.8,
        "plataformas": [(90, 410, 120), (250, 310, 120), (410, 210, 120), (580, 320, 140)],
        "moviles": [(40, 250, 80, 80, 1.5)],
        "enemigos": [(110, 360, "slime"), (270, 260, "hongo"), (430, 160, "slime"),
                     (300, 150, "mosca"), (560, 200, "mosca"), (650, 390, "jefe_final")],
        "monedas": [(130, 360), (290, 260), (450, 160), (620, 270), (60, 200)],
        "picos": [(220, 480), (520, 480)],
        "picos_ciclo": [(340, 480, 0), (380, 480, 450), (420, 480, 900)],
        "pociones": [(440, 180), (620, 290)],
    },
]
TOTAL_NIVELES = len(NIVELES)
TIPOS_JEFE = ("jefe1", "jefe2", "jefe_final")


class Nivel:
    def __init__(self, numero, textura_suelo, ruta_assets):
        datos = NIVELES[numero - 1]
        self.numero = numero
        self.nombre = datos["nombre"]
        self.dificultad = datos["dificultad"]

        self.plataformas = [Plataforma(x, y, w, ALTO_PLAT, textura_suelo) for x, y, w in datos["plataformas"]]
        self.plataformas += [PlataformaMovil(x, y, w, ALTO_PLAT, textura_suelo, rango, vel)
                             for x, y, w, rango, vel in datos["moviles"]]
        self.enemigos = [Enemigo(x, y, t, ruta_assets, self.dificultad) for x, y, t in datos["enemigos"]]

        self.objetos = [Objeto(x, y, "moneda", ruta_assets) for x, y in datos["monedas"]]
        self.objetos += [Objeto(x, y, "picos", ruta_assets) for x, y in datos["picos"]]
        self.objetos += [Objeto(x, y, "picos_ciclo", ruta_assets, fase) for x, y, fase in datos["picos_ciclo"]]
        self.objetos += [Objeto(x, y, "pocion", ruta_assets) for x, y in datos["pociones"]]

    @property
    def jefes_vivos(self):
        return sum(1 for e in self.enemigos if e.vivo and e.tipo in TIPOS_JEFE)

    @property
    def salida_abierta(self):
        return self.jefes_vivos == 0

    def actualizar(self, ahora):
        for p in self.plataformas:
            p.actualizar()
        for o in self.objetos:
            if o.activo:
                o.actualizar(ahora)
