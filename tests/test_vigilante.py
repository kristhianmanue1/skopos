"""Tests para skopos.vigilante (SPEC-005). Runner: `python3 -m unittest`."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pymongo

from skopos.almacenamiento import coleccion_local
from skopos.vigilante import ciclo, descubrir_rollouts, ejecutar

DB_DE_PRUEBA = "skopos_test_vigilante"


def _mongo_disponible() -> bool:
    try:
        pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=500
        ).admin.command("ping")
        return True
    except Exception:
        return False


def _rollout_de_un_turno(path: Path, turn_id: str, texto: str) -> None:
    eventos = [
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": texto}]},
        },
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": turn_id}},
    ]
    path.write_text("\n".join(json.dumps(e) for e in eventos) + "\n", encoding="utf-8")


class DescubrirRolloutsTests(unittest.TestCase):
    def test_directorio_inexistente_no_produce_error(self):
        self.assertEqual(descubrir_rollouts(Path("/no/existe/nada")), set())

    def test_encuentra_jsonl_recursivamente(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            anidado = raiz / "2026" / "08"
            anidado.mkdir(parents=True)
            archivo = anidado / "rollout-x.jsonl"
            archivo.write_text("{}\n", encoding="utf-8")
            (raiz / "no-es-rollout.txt").write_text("x", encoding="utf-8")
            self.assertEqual(descubrir_rollouts(raiz), {archivo})


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class CicloTests(unittest.TestCase):
    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sessions_dir = Path(self.tmp.name)
        self.rollout = self.sessions_dir / "rollout-a.jsonl"
        _rollout_de_un_turno(self.rollout, "t1", "hola")

    def _analizar_fake(self, turno, **_):
        from skopos.analisis import Analisis

        return Analisis(
            tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
            ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
            offset_fin=turno.offset_fin,
        )

    def test_turno_nuevo_queda_guardado(self):
        resultados = ciclo(self.sessions_dir, coleccion=self.coleccion, analizar=self._analizar_fake)
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].estado, "guardado")

    def test_segundo_ciclo_omite_el_turno_ya_guardado(self):
        ciclo(self.sessions_dir, coleccion=self.coleccion, analizar=self._analizar_fake)
        analizar_llamado = []

        def analizar_que_no_deberia_llamarse(turno, **_):
            analizar_llamado.append(turno.turn_id)
            return self._analizar_fake(turno)

        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion, analizar=analizar_que_no_deberia_llamarse
        )
        self.assertEqual(resultados[0].estado, "omitido")
        self.assertEqual(analizar_llamado, [])

    def test_ejecutar_se_detiene_tras_max_ciclos(self):
        ciclos_vistos = []
        ejecutar(
            self.sessions_dir,
            coleccion=self.coleccion,
            intervalo=0,
            max_ciclos=2,
            on_ciclo=lambda resultados: ciclos_vistos.append(resultados),
            analizar=self._analizar_fake,
        )
        self.assertEqual(len(ciclos_vistos), 2)
        # primer ciclo guarda, segundo omite — nunca dos veces "guardado"
        self.assertEqual(ciclos_vistos[0][0].estado, "guardado")
        self.assertEqual(ciclos_vistos[1][0].estado, "omitido")


if __name__ == "__main__":
    unittest.main()
