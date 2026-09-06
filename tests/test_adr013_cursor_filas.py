"""Tests del cursor incremental para orígenes de filas (ADR-013).

Runner: `python3 -m unittest`.

Cobertura: almacén v2 (marcas de agua aditivas sobre v1), extracción
delta con la máquina única (abridores previos, sellos idénticos a la
lectura completa, marca congelada ante fallidos), y el ciclo del
vigilante con la fuente de filas incluida.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from skopos.cursor import AlmacenCursores
from skopos.opencode import extraer_de_base, extraer_delta


# --- Fixture: una base con el formato de opencode -----------------------

ESQUEMA = """
CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT, title TEXT,
                      version TEXT, time_created INTEGER);
CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER,
                      data TEXT);
CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
                   time_created INTEGER, data TEXT);
CREATE INDEX message_session_time_created_id_idx
    ON message (session_id, time_created, id);
CREATE INDEX part_message_id_id_idx ON part (message_id, id);
"""


class _BaseOpencode:
    """Constructor de bases de prueba con filas de opencode."""

    def __init__(self, ruta: Path):
        self.ruta = ruta
        con = sqlite3.connect(ruta)
        con.executescript(ESQUEMA)
        con.commit()
        self.con = con
        self._n = 0

    def _siguiente(self, prefijo: str) -> str:
        self._n += 1
        return f"{prefijo}_{self._n:04d}"

    def sesion(self, sid: str, directorio: str = "/tmp/proyecto",
               version: str = "1.18.27") -> None:
        self.con.execute(
            "INSERT INTO session (id, directory, title, version, time_created) "
            "VALUES (?, ?, ?, ?, ?)", (sid, directorio, sid, version, 1))

    def mensaje(self, sid: str, ms: int, rol: str, texto: str) -> str:
        mid = self._siguiente("msg")
        self.con.execute(
            "INSERT INTO message (id, session_id, time_created, data) "
            "VALUES (?, ?, ?, ?)",
            (mid, sid, ms, json.dumps({"role": rol})))
        pid = self._siguiente("prt")
        self.con.execute(
            "INSERT INTO part (id, message_id, session_id, time_created, data) "
            "VALUES (?, ?, ?, ?, ?)",
            (pid, mid, sid, ms, json.dumps({"type": "text", "text": texto})))
        return mid

    def cerrar(self) -> Path:
        self.con.commit()
        self.con.close()
        return self.ruta


def _base_temporal(test: unittest.TestCase, nombre: str) -> Path:
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    return _BaseOpencode(Path(tmp.name) / nombre).cerrar()


class TestAlmacenV2(unittest.TestCase):
    """skopos-cursores/v2: marcas de filas aditivas sobre las de archivo."""

    def test_v1_carga_sin_marcas_y_guarda_v2(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ruta = Path(tmp.name) / "cursores.json"
        ruta.write_text(json.dumps({
            "version": "skopos-cursores/v1",
            "entradas": {"/x.jsonl": {"offset": 10, "digest_prefijo": "abc"}},
        }), encoding="utf-8")
        almacen = AlmacenCursores(ruta).cargar()
        self.assertIsNotNone(almacen.obtener("/x.jsonl"))
        self.assertIsNone(almacen.obtener_marca("/db"))
        # una marca nueva no borra las entradas de archivo (aditivo)
        almacen.actualizar_marca("/db", 1700000000000)
        almacen.guardar()
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual(datos["version"], "skopos-cursores/v2")
        self.assertIn("/x.jsonl", datos["entradas"])
        self.assertEqual(datos["filas"]["/db"], 1700000000000)

    def test_marca_sobrevive_recarga(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ruta = Path(tmp.name) / "cursores.json"
        almacen = AlmacenCursores(ruta)
        almacen.actualizar_marca("/db", 1234)
        almacen.guardar()
        recargado = AlmacenCursores(ruta).cargar()
        self.assertEqual(recargado.obtener_marca("/db"), 1234)

    def test_podar_olvida_marcas_muertas(self):
        almacen = AlmacenCursores(":memory:")
        almacen._marcas["/viva"] = 1
        eliminadas = almacen.podar(["/viva", "/archivo.jsonl"])
        self.assertEqual(eliminadas, 0)
        eliminadas = almacen.podar(["/otra.jsonl"])
        self.assertEqual(eliminadas, 1)
        self.assertIsNone(almacen.obtener_marca("/viva"))


class TestDelta(unittest.TestCase):
    """La delta contra la misma máquina: sellos idénticos a la completa."""

    def setUp(self):
        self.base = _base_temporal(self, "opencode.db")
        # sesión 1: dos turnos cerrados, ambos pre-ventana
        con = sqlite3.connect(self.base)
        t = 1700000000000
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('m1','s1',?, '{\"role\": \"user\"}')", (t,))
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('m2','s1',?, '{\"role\": \"assistant\"}')", (t + 1000,))
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('m3','s1',?, '{\"role\": \"user\"}')", (t + 2000,))
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('m4','s1',?, '{\"role\": \"assistant\"}')", (t + 3000,))
        # sesión 2: un turno que AÚN NO cierra dentro de la ventana
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('m5','s2',?, '{\"role\": \"user\"}')", (t + 4000,))
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('m6','s2',?, '{\"role\": \"assistant\"}')", (t + 5000,))
        con.commit()
        con.close()
        self.t = t

    def test_delta_igual_a_completa_en_ventana_total(self):
        """Con marca al inicio, la delta emite lo mismo que la completa."""
        completa = [t_.turn_id for t_ in extraer_de_base(self.base).turnos]
        delta, nueva = extraer_delta(self.base, self.t)
        self.assertEqual([t_.turn_id for t_ in delta.turnos], completa)
        self.assertIsNotNone(nueva)

    def test_sellos_delta_igual_completa(self):
        completa = {t_.turn_id: t_ for t_ in extraer_de_base(self.base).turnos}
        delta, _ = extraer_delta(self.base, self.t)
        for turno in delta.turnos:
            self.assertIn(turno.turn_id, completa)
            self.assertEqual(turno.fragmento_sha256,
                             completa[turno.turn_id].fragmento_sha256)
            self.assertEqual(turno.texto_agente,
                             completa[turno.turn_id].texto_agente)

    def test_respuesta_que_cruza_ciclos_sella_completo(self):
        """BLOCKER de la ronda adversarial (2026-09-06): una respuesta que
        tarda más de 2 ciclos deja filas del turno bajo la marca — el
        sello del turno cerrado debe cubrirlas TODAS (igual a completa).
        """
        base = _base_temporal(self, "cruza.db")
        con = sqlite3.connect(base)
        # ciclo 1: sólo el user; la marca nace en max+1
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('b1','s1',?, '{\"role\": \"user\"}')", (self.t,))
        con.commit()
        con.close()
        _, marca1 = extraer_delta(base, None)
        self.assertGreater(marca1, self.t)

        # ciclo 2: primera parte de la respuesta (queda bajo la marca 2)
        con = sqlite3.connect(base)
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('b2','s1',?, '{\"role\": \"assistant\"}')", (self.t + 2000,))
        con.commit()
        con.close()
        extraer_delta(base, marca1)

        # ciclo 3: el resto de la respuesta (cruzó 2 marcas) + cierre user
        con = sqlite3.connect(base)
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('b3','s1',?, '{\"role\": \"assistant\"}')", (self.t + 12000,))
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('b4','s1',?, '{\"role\": \"user\"}')", (self.t + 13000,))
        con.commit()
        con.close()
        tercera, _ = extraer_delta(base, marca1 + 1)
        cerrados = {t_.turn_id for t_ in tercera.turnos}
        self.assertIn("opencode:b1", cerrados)
        completa = {t_.turn_id: t_ for t_ in extraer_de_base(base).turnos}
        sello = next(t_ for t_ in tercera.turnos
                     if t_.turn_id == "opencode:b1").fragmento_sha256
        self.assertEqual(sello, completa["opencode:b1"].fragmento_sha256)
        self.assertEqual(
            len(next(t_ for t_ in tercera.turnos
                     if t_.turn_id == "opencode:b1").origen_ids),
            len(completa["opencode:b1"].origen_ids),
        )  # 3 filas: b1, b2, b3 — ni una menos

    def test_abridor_previo_cruza_la_ventana(self):
        """El turno abierto en s2 cierra DESPUÉS: la delta debe sellarlo
        completo aunque su abridor quede bajo la marca de agua."""
        marca_media = self.t + 4500  # entre m5 (user) y m6 (assistant)
        primera, _ = extraer_delta(self.base, marca_media)
        self.assertEqual(primera.turnos, [])  # el turno de s2 sigue abierto
        # llega el siguiente user que cierra s2
        con = sqlite3.connect(self.base)
        con.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES "
            "('m7','s2',?, '{\"role\": \"user\"}')", (self.t + 6000,))
        con.commit()
        con.close()
        segunda, _ = extraer_delta(self.base, marca_media)
        cerrados = {t_.turn_id for t_ in segunda.turnos}
        self.assertIn("opencode:m5", cerrados)
        completa = {t_.turn_id: t_ for t_ in extraer_de_base(self.base).turnos}
        sello_delta = next(t_ for t_ in segunda.turnos
                           if t_.turn_id == "opencode:m5").fragmento_sha256
        self.assertEqual(sello_delta, completa["opencode:m5"].fragmento_sha256)

    def test_marca_avanza_sin_filas(self):
        _, nueva = extraer_delta(self.base, self.t + 99000)
        self.assertEqual(nueva, self.t + 99000)

    def test_none_delega_en_completa(self):
        completa = extraer_de_base(self.base)
        delta, marca = extraer_delta(self.base, None)
        self.assertEqual(len(delta.turnos), len(completa.turnos))
        # cold start SÍ propone marca (ADR-013 §b): el siguiente ciclo ya es delta
        self.assertIsNotNone(marca)
        self.assertGreater(marca, self.t + 5000)


class TestCicloConFuenteFilas(unittest.TestCase):
    """El ciclo del vigilante procesa la base y persiste la marca."""

    def setUp(self):
        con = sqlite3.connect(":memory:")
        con.close()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        constructor = _BaseOpencode(Path(tmp.name) / "opencode.db")
        t = 1700000000000
        constructor.sesion("s1")
        constructor.mensaje("s1", t, "user", "hola")
        constructor.mensaje("s1", t + 500, "assistant", "mundo")
        constructor.mensaje("s1", t + 1000, "user", "otra pregunta")
        self.base = constructor.cerrar()
        self.t = t
        self.ruta_cursores = Path(tmp.name) / "cursores.json"

    def test_ciclo_persiste_marca_y_dedup_idempotente(self):
        from skopos.vigilante import ciclo

        guardados: list[str] = []

        def _ya_guardado(turn_id, coleccion=None):
            return turn_id in guardados

        def _guardar(analisis, coleccion=None):
            guardados.append(analisis["turn_id"])

        def _analizar(turno, **_):
            return {"turn_id": turno.turn_id}

        def _descubrir(dir_, patron=""):
            return set()

        # pasada 1 (cold start): turno cerrado guardado; el de m3 queda
        # abierto y la marca SE PERSISTE pese a partir de None (ADR-013 §b)
        resultados = ciclo(
            [(Path("/no/existe"), "*.jsonl")],
            coleccion=object(),
            descubrir=_descubrir,
            cursores=AlmacenCursores(self.ruta_cursores).cargar(),
            fuente_filas=self.base,
            ya_guardado=_ya_guardado,
            guardar=_guardar,
            analizar=_analizar,
        )
        self.assertEqual([r.turn_id for r in resultados], ["opencode:msg_0001"])
        self.assertEqual([r.estado for r in resultados], ["guardado"])
        marca = AlmacenCursores(self.ruta_cursores).cargar().obtener_marca(str(self.base))
        self.assertIsNotNone(marca)

        # pasada 2 (sin filas nuevas): nada nuevo que procesar
        resultados = ciclo(
            [(Path("/no/existe"), "*.jsonl")],
            coleccion=object(),
            descubrir=_descubrir,
            cursores=AlmacenCursores(self.ruta_cursores).cargar(),
            fuente_filas=self.base,
            ya_guardado=_ya_guardado,
            guardar=_guardar,
            analizar=_analizar,
        )
        self.assertEqual(resultados, [])
        self.assertEqual(guardados, ["opencode:msg_0001"])  # sin duplicados

    def test_turno_abierto_cierra_en_ciclo_siguiente(self):
        from skopos.vigilante import ciclo

        guardados: list[str] = []

        def _ya_guardado(turn_id, coleccion=None):
            return turn_id in guardados

        def _guardar(analisis, coleccion=None):
            guardados.append(analisis["turn_id"])

        def _analizar(turno, **_):
            return {"turn_id": turno.turn_id}

        def _descubrir(dir_, patron=""):
            return set()

        ciclo(
            [(Path("/no/existe"), "*.jsonl")],
            coleccion=object(),
            descubrir=_descubrir,
            cursores=AlmacenCursores(self.ruta_cursores).cargar(),
            fuente_filas=self.base,
            ya_guardado=_ya_guardado,
            guardar=_guardar,
            analizar=_analizar,
        )
        # llega el cierre del turno abierto (m3): user nuevo + respuesta
        con = sqlite3.connect(self.base)
        for mid, ms, rol, texto in [
            ("m3x", self.t + 1500, "assistant", "respuesta"),
            ("m4x", self.t + 2000, "user", "cierro"),
        ]:
            con.execute(
                "INSERT INTO message (id, session_id, time_created, data) "
                "VALUES (?, 's1', ?, ?)", (mid, ms, json.dumps({"role": rol})))
            con.execute(
                "INSERT INTO part (id, message_id, session_id, time_created, data) "
                "VALUES (?, ?, 's1', ?, ?)",
                (mid + "p", mid, ms, json.dumps({"type": "text", "text": texto})))
        con.commit()
        con.close()
        ciclo(
            [(Path("/no/existe"), "*.jsonl")],
            coleccion=object(),
            descubrir=_descubrir,
            cursores=AlmacenCursores(self.ruta_cursores).cargar(),
            fuente_filas=self.base,
            ya_guardado=_ya_guardado,
            guardar=_guardar,
            analizar=_analizar,
        )
        # el turno abierto en el ciclo 1 cerró y su sello es el del turno completo
        # (el abridor de ese turno es msg_0005: los ids alternan mensaje/part)
        self.assertIn("opencode:msg_0005", guardados)

    def test_fallido_congela_la_marca(self):
        from skopos.vigilante import ciclo
        from skopos.analisis import AnalisisFallido

        intentos: list[str] = []

        def _ya_guardado(turn_id, coleccion=None):
            return False

        def _guardar(analisis, coleccion=None):
            raise AssertionError("no debería llegar")

        def _analizar(turno, **_):
            intentos.append(turno.turn_id)
            raise AnalisisFallido("modelo caído")

        def _descubrir(dir_, patron=""):
            return set()

        almacen = AlmacenCursores(self.ruta_cursores).cargar()
        for _ in range(2):
            ciclo(
                [(Path("/no/existe"), "*.jsonl")],
                coleccion=object(),
                descubrir=_descubrir,
                cursores=almacen,
                fuente_filas=self.base,
                ya_guardado=_ya_guardado,
                guardar=_guardar,
                analizar=_analizar,
            )
        # el turno fallido se ofreció DOS veces: la marca no avanzó (ADR-011)
        self.assertEqual(intentos, ["opencode:msg_0001", "opencode:msg_0001"])
        self.assertIsNone(almacen.obtener_marca(str(self.base)))


if __name__ == "__main__":
    unittest.main()
