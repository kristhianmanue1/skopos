"""Tests de `skopos analyze` — la puerta índice→análisis (ADR-017)."""

import unittest

from pymongo.errors import DuplicateKeyError, OperationFailure

from skopos.analisis import Analisis, ErrorInfraestructura, ErrorModelo
from skopos.analyzer import (
    analyze_document,
    analyze_selection,
    build_filter,
    turn_from_document,
)

DOC_ARCHIVO = {
    "turn_id": "codex-cli:sesion-1:turno-1",
    "session_id": "sesion-1",
    "cli": "codex-cli",
    "ruta_origen": "/tmp/rollout.jsonl",
    "origen_tipo": "archivo",
    "texto_usuario": "commit-write-plan para el hito 23",
    "texto_agente": "hecho",
    "offset_inicio": 0,
    "offset_fin": 120,
    "ocurrido_en": "2026-09-12T10:00:00.000Z",
    "proyecto": "skopos",
    "fragmento_sha256": "abc123",
}

DOC_FILAS = {
    "turn_id": "opencode:sesion-2:turno-9",
    "session_id": "sesion-2",
    "cli": "opencode",
    "ruta_origen": "/tmp/opencode.db",
    "origen_tipo": "filas",
    "origen_tabla": "message",
    "origen_ids": ["fila-1", "fila-2"],
    "texto_usuario": "hola",
    "texto_agente": "qué tal",
    "ocurrido_en": "2026-09-12T11:00:00.000Z",
}


def _analisis(turno):
    return Analisis(
        tema="t", resumen="r", turn_id=turno.turn_id, session_id=turno.session_id,
        ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
        offset_fin=turno.offset_fin, cli=turno.cli, modelo_analisis="qwen3:8b",
    )


class ReconstruirTurno(unittest.TestCase):
    def test_origen_de_archivo_conserva_offsets_y_sello(self):
        turno = turn_from_document(DOC_ARCHIVO)
        self.assertEqual(turno.turn_id, DOC_ARCHIVO["turn_id"])
        self.assertEqual((turno.offset_inicio, turno.offset_fin), (0, 120))
        self.assertEqual(turno.fragmento_sha256, "abc123")
        self.assertEqual(turno.proyecto, "skopos")

    def test_ocurrido_en_vuelve_a_ser_timestamp_cierre(self):
        # el mismo dato con el nombre que le toca a cada lado de la frontera
        turno = turn_from_document(DOC_ARCHIVO)
        self.assertEqual(turno.timestamp_cierre, DOC_ARCHIVO["ocurrido_en"])

    def test_origen_de_filas_sin_offsets_no_los_inventa(self):
        # ADR-012: una fila no tiene rango de bytes estable
        turno = turn_from_document(DOC_FILAS)
        self.assertIsNone(turno.offset_inicio)
        self.assertIsNone(turno.offset_fin)
        self.assertEqual(turno.origen_tabla, "message")
        self.assertEqual(turno.origen_ids, ("fila-1", "fila-2"))

    def test_documento_incompleto_no_revienta(self):
        turno = turn_from_document({"turn_id": "x"})
        self.assertEqual(turno.turn_id, "x")
        self.assertEqual(turno.texto_usuario, "")


class ConstruirFiltro(unittest.TestCase):
    def test_sin_criterios_es_filtro_vacio(self):
        self.assertEqual(build_filter(), {})

    def test_ejes_de_c9(self):
        filtro = build_filter(project="skopos", cli="codex-cli")
        self.assertEqual(filtro, {"proyecto": "skopos", "cli": "codex-cli"})

    def test_ancla_busca_en_los_dos_campos_de_texto(self):
        filtro = build_filter(anchor="commit-write-plan")
        campos = {list(clausula)[0] for clausula in filtro["$or"]}
        self.assertEqual(campos, {"texto_usuario", "texto_agente"})

    def test_ancla_escapa_el_literal(self):
        # un ancla con metacaracteres es un literal, no una regex del usuario
        filtro = build_filter(anchor="a.b*c")
        self.assertIn(r"a\.b\*c", filtro["$or"][0]["texto_usuario"]["$regex"])

    def test_rango_de_fechas(self):
        filtro = build_filter(since="2026-09-01", until="2026-09-12")
        self.assertEqual(filtro["ocurrido_en"],
                         {"$gte": "2026-09-01", "$lte": "2026-09-12"})


class _ColeccionFalsa:
    """Colección mínima: registra lo guardado y responde la dedup."""

    def __init__(self, ya_analizados=()):
        self.ya = set(ya_analizados)
        self.guardados = []


def _ya_analizado_de(coleccion):
    def _ya(turn_id, *, coleccion=None):
        return turn_id in coleccion.ya if coleccion else False
    return _ya


class AnalizarDocumento(unittest.TestCase):
    def setUp(self):
        self.coleccion = _ColeccionFalsa()
        self.llamadas = []

    def _analizar(self, turno, **kwargs):
        self.llamadas.append(turno.turn_id)
        return _analisis(turno)

    def _guardar(self, analisis, *, coleccion):
        coleccion.guardados.append(analisis)
        return {}

    def _correr(self, documento, **kwargs):
        opciones = dict(
            analysis_collection=self.coleccion, analyze=self._analizar,
            save=self._guardar,
            already_analyzed=lambda tid, *, coleccion: tid in coleccion.ya,
            sleep_for=lambda segundos: None,
        )
        opciones.update(kwargs)
        return analyze_document(documento, **opciones)

    def test_turno_sin_analisis_se_analiza_y_se_guarda(self):
        self.assertEqual(self._correr(DOC_ARCHIVO), "analizado")
        self.assertEqual(len(self.coleccion.guardados), 1)

    def test_turno_con_analisis_previo_no_se_toca(self):
        # ADR-017 (b): el supersede es territorio exclusivo de reanalizar
        self.coleccion.ya.add(DOC_ARCHIVO["turn_id"])
        self.assertEqual(self._correr(DOC_ARCHIVO), "ya_analizado")
        self.assertEqual(self.llamadas, [])
        self.assertEqual(self.coleccion.guardados, [])

    def test_turno_vacio_no_gasta_una_llamada_al_modelo(self):
        documento = dict(DOC_ARCHIVO, texto_usuario="", texto_agente="")
        self.assertEqual(self._correr(documento), "sin_contenido")
        self.assertEqual(self.llamadas, [])

    def test_documento_sin_turn_id_es_invalido(self):
        self.assertEqual(self._correr({"texto_usuario": "x"}), "invalido")

    def test_fallo_del_modelo_no_se_reintenta(self):
        # analisis.py: reintentar lo mismo probablemente falle igual, y
        # gastar tres llamadas para confirmarlo quema cuota ajena
        intentos = []

        def _reventar(turno, **kwargs):
            intentos.append(1)
            raise ErrorModelo("sin JSON")
        self.assertEqual(
            self._correr(DOC_ARCHIVO, analyze=_reventar, sleep_for=lambda s: None),
            "fallido_modelo",
        )
        self.assertEqual(len(intentos), 1)

    def test_429_del_proveedor_se_reintenta_y_puede_salir_bien(self):
        # el 28 % de fallos de la primera corrida del piloto fue esto
        intentos = []

        def _intermitente(turno, **kwargs):
            intentos.append(1)
            if len(intentos) < 3:
                raise ErrorInfraestructura("HTTP Error 429: Too Many Requests")
            return _analisis(turno)
        esperas = []
        self.assertEqual(
            self._correr(DOC_ARCHIVO, analyze=_intermitente,
                         sleep_for=esperas.append),
            "analizado",
        )
        self.assertEqual(len(intentos), 3)
        self.assertEqual(esperas, [5.0, 15.0])  # espera creciente

    def test_proveedor_caido_agota_reintentos_y_se_distingue(self):
        intentos = []

        def _caido(turno, **kwargs):
            intentos.append(1)
            raise ErrorInfraestructura("timeout")
        self.assertEqual(
            self._correr(DOC_ARCHIVO, analyze=_caido, retries=2,
                         sleep_for=lambda s: None),
            "fallido_infraestructura",
        )
        self.assertEqual(len(intentos), 3)  # 1 intento + 2 reintentos

    def test_duplicado_concurrente_cuenta_como_ya_analizado(self):
        def _duplicado(analisis, *, coleccion):
            raise DuplicateKeyError("carrera")
        self.assertEqual(self._correr(DOC_ARCHIVO, save=_duplicado),
                         "ya_analizado")

    def test_mongo_caido_en_la_dedup_es_fallo_no_reanalisis(self):
        def _reventar(turn_id, *, coleccion):
            raise OperationFailure("mongo caído")
        self.assertEqual(self._correr(DOC_ARCHIVO, already_analyzed=_reventar),
                         "fallido")
        self.assertEqual(self.llamadas, [])


class AnalizarSeleccion(unittest.TestCase):
    def setUp(self):
        self.coleccion = _ColeccionFalsa()

    def _opciones(self, **kwargs):
        base = dict(
            analysis_collection=self.coleccion,
            analyze=lambda turno, **k: _analisis(turno),
            save=lambda a, *, coleccion: coleccion.guardados.append(a),
            already_analyzed=lambda tid, *, coleccion: tid in coleccion.ya,
            sleep_for=lambda segundos: None,
        )
        base.update(kwargs)
        return base

    def test_resumen_cuenta_cada_destino(self):
        self.coleccion.ya.add(DOC_FILAS["turn_id"])
        resumen = analyze_selection([DOC_ARCHIVO, DOC_FILAS], **self._opciones())
        self.assertEqual(resumen["analizado"], 1)
        self.assertEqual(resumen["ya_analizado"], 1)

    def test_interrupcion_devuelve_lo_hecho_y_se_marca_parcial(self):
        # una corrida de 3 h se puede parar: el resumen debe ser verdadero
        def _analizar(turno, **kwargs):
            if turno.turn_id == DOC_FILAS["turn_id"]:
                raise KeyboardInterrupt
            return _analisis(turno)
        resumen = analyze_selection(
            [DOC_ARCHIVO, DOC_FILAS], **self._opciones(analyze=_analizar)
        )
        self.assertEqual(resumen["analizado"], 1)
        self.assertEqual(resumen["interrumpido"], 1)
        self.assertEqual(len(self.coleccion.guardados), 1)

    def test_pausa_proactiva_espera_entre_peticiones_no_antes_de_la_primera(self):
        esperas = []
        analyze_selection(
            [DOC_ARCHIVO, DOC_FILAS], pause=2.0, sleep_for=esperas.append,
            **{k: v for k, v in self._opciones().items() if k != "sleep_for"},
        )
        self.assertEqual(esperas, [2.0])  # 2 turnos → 1 pausa, no 2

    def test_sin_pausa_no_se_duerme(self):
        esperas = []
        analyze_selection(
            [DOC_ARCHIVO, DOC_FILAS], sleep_for=esperas.append,
            **{k: v for k, v in self._opciones().items() if k != "sleep_for"},
        )
        self.assertEqual(esperas, [])

    def test_progreso_se_reporta_por_turno(self):
        vistos = []
        analyze_selection(
            [DOC_ARCHIVO],
            on_progress=lambda i, doc, destino: vistos.append((i, destino)),
            **self._opciones(),
        )
        self.assertEqual(vistos, [(1, "analizado")])


if __name__ == "__main__":
    unittest.main()
