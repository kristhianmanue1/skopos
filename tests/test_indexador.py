"""Tests del índice de turnos (P-004, documento-turno-mongo v1).

Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pymongo

from skopos.almacenamiento import (
    DocumentoInvalido,
    _documento_turno,
    coleccion_turnos,
    indexar_turno,
)
from skopos.captura import Turno
from skopos.indexador import descubrir, indexar

DB_DE_PRUEBA = "skopos_test_indexador"


def _mongo_disponible() -> bool:
    try:
        pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=500
        ).server_info()
        return True
    except Exception:
        return False


def _turno(turn_id: str = "t1", **extra) -> Turno:
    campos = dict(
        turn_id=turn_id, session_id="s1", texto_usuario="pregunta",
        texto_agente="respuesta", timestamp_cierre="2026-08-28T10:00:00Z",
        ruta_origen="/x/rollout.jsonl", offset_inicio=0, offset_fin=100,
        cli="codex-cli", proyecto="skopos", fragmento_sha256="a" * 64,
    )
    campos.update(extra)
    return Turno(**campos)


class DocumentoTests(unittest.TestCase):
    def test_lleva_el_texto_del_turno_y_sus_referencias(self):
        d = _documento_turno(_turno())
        self.assertEqual(d["texto_usuario"], "pregunta")
        self.assertEqual(d["texto_agente"], "respuesta")
        self.assertEqual(d["ocurrido_en"], "2026-08-28T10:00:00Z")
        self.assertEqual(d["fragmento_sha256"], "a" * 64)
        self.assertIn("indexado_en", d)

    def test_no_inventa_campos_opcionales_ausentes(self):
        d = _documento_turno(_turno(proyecto=None, timestamp_cierre=None,
                                    fragmento_sha256=None))
        for clave in ("proyecto", "ocurrido_en", "fragmento_sha256"):
            self.assertNotIn(clave, d)

    def test_no_guarda_analisis_ni_modelo(self):
        # un turno es un hecho observado; tema/resumen/modelo son de la
        # coleccion de analisis, no de esta
        d = _documento_turno(_turno())
        for clave in ("tema", "resumen", "modelo_analisis", "version"):
            self.assertNotIn(clave, d)


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class IndexarTests(unittest.TestCase):
    def setUp(self):
        self.coleccion = coleccion_turnos(db=DB_DE_PRUEBA)
        self.addCleanup(self.coleccion.database.client.drop_database, DB_DE_PRUEBA)
        self.coleccion.delete_many({})

    def test_indexa_y_deduplica_sin_reescribir(self):
        self.assertTrue(indexar_turno(_turno(), coleccion=self.coleccion))
        self.assertFalse(indexar_turno(_turno(), coleccion=self.coleccion))
        self.assertEqual(self.coleccion.count_documents({}), 1)

    def test_turno_sin_identidad_se_rechaza_en_el_borde(self):
        with self.assertRaises(DocumentoInvalido):
            indexar_turno(_turno(turn_id=""), coleccion=self.coleccion)
        self.assertEqual(self.coleccion.count_documents({}), 0)

    def test_se_busca_por_texto_crudo(self):
        indexar_turno(_turno(turn_id="t1", texto_usuario="cómo indexo en mongo"),
                      coleccion=self.coleccion)
        indexar_turno(_turno(turn_id="t2", texto_usuario="receta de tortilla"),
                      coleccion=self.coleccion)
        hallados = [d["turn_id"] for d in
                    self.coleccion.find({"$text": {"$search": "mongo"}})]
        self.assertEqual(hallados, ["t1"])

    def test_no_escribe_en_la_coleccion_de_analisis(self):
        indexar_turno(_turno(), coleccion=self.coleccion)
        analisis = self.coleccion.database["analisis"]
        self.assertEqual(analisis.count_documents({}), 0)


class RecorridoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _rollout(self, nombre: str, turnos: list[str]) -> Path:
        eventos = [{"type": "session_meta", "payload": {"originator": "codex-tui"}}]
        for t in turnos:
            eventos.append({"type": "response_item", "payload": {
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": f"texto {t}"}]}})
            eventos.append({"type": "event_msg",
                            "payload": {"type": "task_complete", "turn_id": t}})
        path = self.dir / nombre
        path.write_text("\n".join(json.dumps(e) for e in eventos) + "\n", encoding="utf-8")
        return path

    def test_descubrir_recorre_directorios_y_acepta_archivos_sueltos(self):
        a = self._rollout("rollout-a.jsonl", ["t1"])
        self.assertEqual(descubrir([self.dir], "*.jsonl"), [a])
        self.assertEqual(descubrir([a], "*.jsonl"), [a])

    def test_el_limite_corta_por_archivos_y_declara_lo_no_visitado(self):
        # cortar a mitad de archivo dejaria un prefijo arbitrario de una
        # sesion; el limite es por unidades completas
        self._rollout("rollout-a.jsonl", ["t1"])
        self._rollout("rollout-b.jsonl", ["t2"])
        rutas = descubrir([self.dir], "*.jsonl")

        class _Falsa:
            def __init__(self): self.docs = []
            def insert_one(self, d): self.docs.append(d)

        resumen = indexar(rutas, coleccion=_Falsa(), limite=1)
        self.assertEqual(resumen["archivo:ok"], 1)
        self.assertEqual(resumen["archivo:no_visitado"], 1)

    def test_los_archivos_ajenos_se_contabilizan_por_diagnostico(self):
        (self.dir / "ajeno.jsonl").write_text('{"type":"otro"}\n', encoding="utf-8")

        class _Falsa:
            def insert_one(self, d): pass

        resumen = indexar(descubrir([self.dir], "*.jsonl"), coleccion=_Falsa())
        self.assertEqual(resumen["archivo:formato_desconocido"], 1)


if __name__ == "__main__":
    unittest.main()
