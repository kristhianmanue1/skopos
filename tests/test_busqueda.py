"""Tests de `skopos buscar` — primera superficie que sirve texto crudo.

Comprueba las mitigaciones que P-004 exigió extender desde ADR-009:
P3 (declaración), P5 (presupuesto) y redacción de secretos.
Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import unittest

import pymongo

from skopos.almacenamiento import coleccion_turnos, indexar_turno
from skopos.busqueda import DECLARACION_P3, buscar
from skopos.captura import Turno

DB_DE_PRUEBA = "skopos_test_busqueda"


def _mongo_disponible() -> bool:
    try:
        pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=500
        ).server_info()
        return True
    except Exception:
        return False


def _turno(turn_id: str, usuario: str, agente: str = "", **extra) -> Turno:
    campos = dict(
        turn_id=turn_id, session_id="s1", texto_usuario=usuario, texto_agente=agente,
        timestamp_cierre="2026-08-28T10:00:00Z", ruta_origen="/x/rollout.jsonl",
        offset_inicio=0, offset_fin=10, cli="codex-cli", proyecto="skopos",
    )
    campos.update(extra)
    return Turno(**campos)


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class BuscarTests(unittest.TestCase):
    def setUp(self):
        self.coleccion = coleccion_turnos(db=DB_DE_PRUEBA)
        self.addCleanup(self.coleccion.database.client.drop_database, DB_DE_PRUEBA)
        self.coleccion.delete_many({})

    def _indexar(self, *turnos):
        for t in turnos:
            indexar_turno(t, coleccion=self.coleccion)

    def test_la_salida_declara_que_el_texto_es_dato_no_instruccion(self):
        # P3 (ADR-009): la declaración no impide nada por sí sola, por eso
        # viene con P5 al lado; pero sin ella el consumidor no sabe qué
        # está leyendo
        self._indexar(_turno("t1", "hola mongo"))
        self.assertEqual(buscar("mongo", coleccion=self.coleccion)["declaracion"],
                         DECLARACION_P3)

    def test_el_limite_acota_y_cuenta_lo_excluido(self):
        self._indexar(*[_turno(f"t{i}", "mongo va aquí") for i in range(5)])
        salida = buscar("mongo", coleccion=self.coleccion, max_resultados=2)
        self.assertEqual(len(salida["resultados"]), 2)
        self.assertEqual(salida["excluidos"]["por_limite"], 3)

    def test_max_cero_no_sirve_nada_pero_cuenta_todo(self):
        self._indexar(_turno("t1", "mongo"), _turno("t2", "mongo"))
        salida = buscar("mongo", coleccion=self.coleccion, max_resultados=0)
        self.assertEqual(salida["resultados"], [])
        self.assertEqual(salida["excluidos"]["por_limite"], 2)

    def test_el_texto_largo_se_trunca_con_marcador(self):
        self._indexar(_turno("t1", "mongo " + "x" * 5000))
        salida = buscar("mongo", coleccion=self.coleccion, tope_texto=100)
        resultado = salida["resultados"][0]
        self.assertTrue(resultado["truncado"])
        self.assertIn("texto truncado", resultado["texto_usuario"])
        self.assertIn("de 5006 bytes", resultado["texto_usuario"])

    def test_los_secretos_se_redactan_antes_de_servir(self):
        # en `skopos query` la redacción protegía tema/resumen; aquí
        # protege la conversación, que es donde viven las credenciales
        self._indexar(_turno("t1", 'mongo export API_KEY=sk-abcdefghijklmnop1234'))
        servido = buscar("mongo", coleccion=self.coleccion)["resultados"][0]
        self.assertNotIn("sk-abcdefghijklmnop1234", servido["texto_usuario"])

    def test_filtra_por_proyecto_y_por_cli(self):
        self._indexar(
            _turno("t1", "mongo aquí", proyecto="skopos", cli="codex-cli"),
            _turno("t2", "mongo allá", proyecto="otro", cli="claude-code"),
        )
        solo_skopos = buscar("mongo", coleccion=self.coleccion, proyecto="skopos")
        self.assertEqual([r["turn_id"] for r in solo_skopos["resultados"]], ["t1"])
        solo_claude = buscar("mongo", coleccion=self.coleccion, cli="claude-code")
        self.assertEqual([r["turn_id"] for r in solo_claude["resultados"]], ["t2"])

    def test_ordena_por_relevancia(self):
        # sin orden, `$text` (que une con OR) devuelve lo primero que
        # encuentra y la búsqueda es inservible
        self._indexar(
            _turno("flojo", "una mención suelta de mongo"),
            _turno("fuerte", "mongo mongo mongo índice mongo"),
        )
        resultados = buscar("mongo", coleccion=self.coleccion)["resultados"]
        self.assertEqual(resultados[0]["turn_id"], "fuerte")
        self.assertGreater(resultados[0]["relevancia"], resultados[1]["relevancia"])

    def test_sirve_el_localizador_del_origen(self):
        self._indexar(_turno("t1", "mongo"))
        resultado = buscar("mongo", coleccion=self.coleccion)["resultados"][0]
        self.assertEqual(resultado["ruta_origen"], "/x/rollout.jsonl")
        self.assertEqual(resultado["origen_tipo"], "archivo")


if __name__ == "__main__":
    unittest.main()
