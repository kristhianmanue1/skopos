"""Tests para skopos.almacenamiento (SPEC-003), contra Mongo local real.

Se salta automáticamente si no hay MongoDB corriendo en localhost:27017,
en vez de fallar la suite (mismo patrón que la integración de Ollama en
test_analisis.py).
"""

from __future__ import annotations

import unittest

import pymongo
from pymongo.errors import DuplicateKeyError, PyMongoError

from skopos.almacenamiento import (
    DocumentoInvalido,
    TurnoInexistente,
    buscar_por_tema,
    coleccion_local,
    existe_turn_id,
    guardar_analisis,
    superseder_documento,
    version_vigente,
)
from skopos.analisis import Analisis

DB_DE_PRUEBA = "skopos_test"


def _mongo_disponible() -> bool:
    try:
        pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=500
        ).admin.command("ping")
        return True
    except Exception:
        return False


def _analisis_ejemplo(tema="bases de datos", turn_id="t1", resumen="explica MongoDB") -> Analisis:
    return Analisis(
        tema=tema,
        resumen=resumen,
        turn_id=turn_id,
        session_id="s1",
        ruta_origen="/tmp/rollout-test.jsonl",
        offset_inicio=0,
        offset_fin=100,
        cli="codex-cli", modelo_analisis="test-modelo",
        entidades=["MongoDB"],
    )


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class AlmacenamientoTests(unittest.TestCase):
    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

    def test_guardar_y_recuperar_por_tema(self):
        guardar_analisis(_analisis_ejemplo(), coleccion=self.coleccion)
        resultados = buscar_por_tema("bases de datos", coleccion=self.coleccion)
        self.assertEqual(len(resultados), 1)
        documento = resultados[0]
        self.assertEqual(documento["turn_id"], "t1")
        self.assertEqual(documento["ruta_origen"], "/tmp/rollout-test.jsonl")
        self.assertEqual(documento["offset_inicio"], 0)
        self.assertEqual(documento["offset_fin"], 100)
        self.assertIn("creado_en", documento)

    def test_tema_sin_coincidencias_devuelve_lista_vacia(self):
        guardar_analisis(_analisis_ejemplo(), coleccion=self.coleccion)
        self.assertEqual(buscar_por_tema("tema inexistente", coleccion=self.coleccion), [])

    def test_campos_opcionales_ausentes_no_se_guardan_vacios(self):
        analisis = _analisis_ejemplo()
        guardar_analisis(analisis, coleccion=self.coleccion)
        documento = buscar_por_tema("bases de datos", coleccion=self.coleccion)[0]
        self.assertNotIn("dominio", documento)
        self.assertNotIn("metadata_cli", documento)

    def test_dominio_y_metadata_cli_se_guardan_si_estan_presentes(self):
        analisis = Analisis(
            tema="arquitectura",
            resumen="discute microservicios",
            turn_id="t2",
            session_id="s1",
            ruta_origen="/tmp/rollout-test.jsonl",
            offset_inicio=100,
            offset_fin=200,
            cli="codex-cli", modelo_analisis="test-modelo",
            dominio="arquitectura-software",
            metadata_cli={"cli_producto": {"nombre": "codex-cli"}},
        )
        guardar_analisis(analisis, coleccion=self.coleccion)
        documento = buscar_por_tema("arquitectura", coleccion=self.coleccion)[0]
        self.assertEqual(documento["dominio"], "arquitectura-software")
        self.assertEqual(documento["metadata_cli"]["cli_producto"]["nombre"], "codex-cli")

    def test_documento_siempre_resoluble_al_fragmento_de_origen(self):
        guardar_analisis(_analisis_ejemplo(), coleccion=self.coleccion)
        documento = buscar_por_tema("bases de datos", coleccion=self.coleccion)[0]
        for campo in ("ruta_origen", "offset_inicio", "offset_fin"):
            self.assertIn(campo, documento)

    def test_existe_turn_id_antes_y_despues_de_guardar(self):
        self.assertFalse(existe_turn_id("t1", coleccion=self.coleccion))
        guardar_analisis(_analisis_ejemplo(turn_id="t1"), coleccion=self.coleccion)
        self.assertTrue(existe_turn_id("t1", coleccion=self.coleccion))
        self.assertFalse(existe_turn_id("otro-turno", coleccion=self.coleccion))

    def test_turn_id_duplicado_lo_rechaza_el_indice_unico(self):
        # ronda adversarial 2026-08-13 [HIGH]: sin índice único, dos
        # inserciones para el mismo turn_id convivían sin error.
        guardar_analisis(_analisis_ejemplo(turn_id="dup"), coleccion=self.coleccion)
        with self.assertRaises(DuplicateKeyError):
            guardar_analisis(_analisis_ejemplo(turn_id="dup"), coleccion=self.coleccion)

    def test_guardar_sin_turn_id_o_ruta_origen_se_rechaza(self):
        # ronda adversarial 2026-08-13 [HIGH]: el CONTRATO prometía rechazo
        # en el borde; el código sólo confiaba en que nunca pasara.
        sin_turn_id = _analisis_ejemplo(turn_id="")
        with self.assertRaises(DocumentoInvalido):
            guardar_analisis(sin_turn_id, coleccion=self.coleccion)
        self.assertEqual(self.coleccion.count_documents({}), 0)

    def test_busqueda_por_tema_encuentra_reformulaciones_con_palabras_en_comun(self):
        # ronda adversarial 2026-08-13 [HIGH]: igualdad exacta fallaba
        # contra temas que el LLM redacta distinto para la misma idea.
        guardar_analisis(
            _analisis_ejemplo(tema="Índices en MongoDB", turn_id="t1"),
            coleccion=self.coleccion,
        )
        guardar_analisis(
            _analisis_ejemplo(tema="Optimización de consulta en MongoDB", turn_id="t2"),
            coleccion=self.coleccion,
        )
        guardar_analisis(
            _analisis_ejemplo(tema="Recetas de cocina", turn_id="t3", resumen="pasta al pesto"),
            coleccion=self.coleccion,
        )
        resultados = buscar_por_tema("Índices MongoDB", coleccion=self.coleccion)
        turn_ids = {r["turn_id"] for r in resultados}
        self.assertIn("t1", turn_ids)
        self.assertIn("t2", turn_ids)
        self.assertNotIn("t3", turn_ids)


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class SupersedeTests(unittest.TestCase):
    """ADR-007 (alternativa B, decisión 🔒 2026-08-20): versiones por
    inserción, vigente = número mayor, insert-only físico intacto."""

    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

    def test_primera_version_es_1(self):
        guardar_analisis(_analisis_ejemplo(turn_id="v1"), coleccion=self.coleccion)
        doc = version_vigente("v1", coleccion=self.coleccion)
        self.assertEqual(doc["version"], 1)

    def test_indice_unico_compuesto_y_no_simple(self):
        nombres = {i["name"] for i in self.coleccion.list_indexes()}
        self.assertIn("turn_id_1_version_1", nombres)
        self.assertNotIn("turn_id_1", nombres)

    def test_coleccion_local_retira_indice_unico_simple_pre_v2(self):
        # H5 de la ronda 2 del ADR-007: el bootstrap baja el índice viejo
        # si un despliegue pre-v2 lo dejó (se recrea a mano y se reconecta)
        self.coleccion.create_index("turn_id", unique=True)
        coleccion_retirada = coleccion_local(db=DB_DE_PRUEBA)
        cliente_extra = coleccion_retirada.database.client
        self.addCleanup(cliente_extra.close)
        nombres = {i["name"] for i in self.coleccion.list_indexes()}
        self.assertNotIn("turn_id_1", nombres)

    def test_supersede_copia_y_sustituye_sin_tocar_la_vieja(self):
        guardar_analisis(
            _analisis_ejemplo(turn_id="v2", tema="tema original"),
            coleccion=self.coleccion,
        )
        nueva = superseder_documento(
            "v2", {"tema": "tema corregido"}, coleccion=self.coleccion
        )
        self.assertEqual(nueva["version"], 2)
        self.assertEqual(nueva["tema"], "tema corregido")
        # el resto se copia hacia adelante
        self.assertEqual(nueva["resumen"], _analisis_ejemplo().resumen)
        # la versión 1 permanece intacta (auditoría, insert-only físico)
        vieja = next(
            d for d in self.coleccion.find({"turn_id": "v2"}) if d["version"] == 1
        )
        self.assertEqual(vieja["tema"], "tema original")

    def test_supersede_reintenta_con_version_recomputada(self):
        # H2 de la ronda 2 del ADR-007: choque concurrente por la misma
        # versión → re-cómputo de max(versión) y reintento, nunca silencio
        guardar_analisis(_analisis_ejemplo(turn_id="v3"), coleccion=self.coleccion)
        # un "concurrente" inserta la versión 2 entre nuestro cálculo y
        # nuestra inserción: simulamos el choque una vez
        inserciones = {"n": 0}
        insert_one_real = self.coleccion.insert_one

        def insert_one_con_choque(doc, *args, **kwargs):
            if doc.get("turn_id") == "v3" and doc.get("version") == 2:
                inserciones["n"] += 1
                if inserciones["n"] == 1:
                    self.coleccion.insert_one = insert_one_real
                    # el concurrente gana la versión 2
                    ganador = dict(doc)
                    ganador["_id"] = None
                    insert_one_real(
                        {k: v for k, v in ganador.items() if k != "_id"}
                    )
                    # la nuestra debe chocar con el índice único
                    return insert_one_real(doc)
            return insert_one_real(doc, *args, **kwargs)

        self.coleccion.insert_one = insert_one_con_choque
        nueva = superseder_documento(
            "v3", {"tema": "tema tras choque"}, coleccion=self.coleccion
        )
        self.assertEqual(nueva["version"], 3)
        self.assertEqual(nueva["tema"], "tema tras choque")

    def test_supersede_de_turno_inexistente_falla_explicito(self):
        with self.assertRaises(TurnoInexistente):
            superseder_documento("no-existe", {"tema": "x"}, coleccion=self.coleccion)

    def test_buscar_por_tema_sirve_solo_la_vigente(self):
        # carga de seguridad (H1 de la ronda 2): la versión vieja con el
        # secreto en claro no se sirve nunca por las lecturas públicas
        guardar_analisis(
            _analisis_ejemplo(turn_id="v4", tema="despliegue con sk-AAAABBBBCCCCDDDD"),
            coleccion=self.coleccion,
        )
        superseder_documento(
            "v4", {"tema": "despliegue con [REDACTADO]"}, coleccion=self.coleccion
        )
        resultados = buscar_por_tema("despliegue", coleccion=self.coleccion)
        self.assertEqual(len(resultados), 1)
        self.assertNotIn("sk-AAAABBBBCCCCDDDD", resultados[0]["tema"])

    def test_existe_turn_id_casa_cualquier_version(self):
        guardar_analisis(_analisis_ejemplo(turn_id="v5"), coleccion=self.coleccion)
        superseder_documento("v5", {"tema": "x"}, coleccion=self.coleccion)
        self.assertTrue(existe_turn_id("v5", coleccion=self.coleccion))

    def test_supersede_de_legado_sin_version_produce_version_1(self):
        # ronda 3, F6: documento pre-v2 sin campo version — su primer
        # supersede es la versión 1, no salta a la 2
        self.coleccion.insert_one(
            {
                "tema": "legado",
                "resumen": "escrito antes de ADR-007",
                "turn_id": "v6",
                "ruta_origen": "/tmp/rollout.jsonl",
                "offset_inicio": 0,
                "offset_fin": 10,
                "cli": "codex-cli",
                "modelo_analisis": "viejo",
                "creado_en": "2026-08-01T00:00:00+00:00",
            }
        )
        nueva = superseder_documento(
            "v6", {"tema": "moderno"}, coleccion=self.coleccion
        )
        self.assertEqual(nueva["version"], 1)
        self.assertEqual(nueva["tema"], "moderno")

    def test_supersede_agota_reintentos_y_falla_explicito(self):
        # ronda 3, F9: 3 choques seguidos → PyMongoError, nunca silencio
        guardar_analisis(_analisis_ejemplo(turn_id="v7"), coleccion=self.coleccion)
        insert_one_real = self.coleccion.insert_one

        def insert_one_siempre_choca(doc, *args, **kwargs):
            if doc.get("turn_id") == "v7":
                raise DuplicateKeyError("choque simulado")
            return insert_one_real(doc, *args, **kwargs)

        self.coleccion.insert_one = insert_one_siempre_choca
        with self.assertRaises(PyMongoError) as ctx:
            superseder_documento("v7", {"tema": "x"}, coleccion=self.coleccion)
        self.assertIn("choques", str(ctx.exception))

    def test_supersede_rechaza_claves_de_identidad(self):
        # ronda 3, F3: el supersede repara análisis, nunca re-apunta la
        # referencia de origen
        guardar_analisis(_analisis_ejemplo(turn_id="v8"), coleccion=self.coleccion)
        for prohibida in ("turn_id", "version", "_id", "ruta_origen"):
            with self.subTest(clave=prohibida):
                with self.assertRaises(DocumentoInvalido):
                    superseder_documento(
                        "v8", {prohibida: "otra-cosa"}, coleccion=self.coleccion
                    )


if __name__ == "__main__":
    unittest.main()
