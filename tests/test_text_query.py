"""Regresión de tildes: sintaxis preservada y recuperación real en índice español."""
import unittest
import uuid
import io
from contextlib import redirect_stdout
from unittest.mock import patch
import pymongo
from skopos.text_query import expand_accents
from skopos.busqueda import buscar
from skopos.cli import query


class ExpansionTests(unittest.TestCase):
    def test_cli_flags_reach_both_consumers_without_real_connections(self):
        from skopos.cli import query_command
        from skopos.busqueda import buscar_command
        for command, factory, consumer in (
                (query_command, 'skopos.cli.coleccion_local', 'skopos.cli.query'),
                (buscar_command, 'skopos.busqueda.coleccion_turnos', 'skopos.busqueda.buscar')):
            for enabled in (False, True):
                with patch(factory), patch(consumer, return_value={}) as operation, \
                        redirect_stdout(io.StringIO()):
                    self.assertEqual(command(['reparacion'] + (['--expand-accents'] if enabled else [])), 0)
                    self.assertEqual(operation.call_args.kwargs['expand_accents'], enabled)

    def test_simple_negative_case_and_technical_tokens(self):
        for original, expected in (
                ('reparacion', 'reparacion reparación'),
                ('REPARACION', 'REPARACION REPARACIÓN'),
                ('indice -reparacion', 'indice -reparacion -reparación'),
                ('"reparacion exacta"', '"reparacion exacta"'),
                ('"frase exacta" reparacion', '"frase exacta" reparacion reparación'),
                ('reparacion.py x_reparacion https://x/reparacion',
                 'reparacion.py x_reparacion https://x/reparacion'),
                ('"reparacion', '"reparacion'),
                ('x"reparacion exacta"', 'x"reparacion exacta"'),
                ('"frase"reparacion', '"frase"reparacion'),
                ('"frase" -reparacion', '"frase" -reparacion -reparación'),
                ('İnformacion', 'İnformacion'),
                ('x\\reparacion', 'x\\reparacion'),
                ('reparación avión cafe acción', 'reparación avión cafe acción'),
                ('  reparacion\tvalidacion ', '  reparacion reparación\tvalidacion validación ')):
            with self.subTest(original=original):
                self.assertEqual(expand_accents(original), expected)


class SpanishIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = pymongo.MongoClient('mongodb://localhost:27017',serverSelectionTimeoutMS=1000)
        try:
            cls.client.admin.command('ping')
        except pymongo.errors.PyMongoError:
            cls.client.close()
            raise unittest.SkipTest('Mongo de pruebas no disponible')
        cls.db = cls.client['skopos_test_accents_' + uuid.uuid4().hex]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db.name)
        cls.client.close()

    def setUp(self):
        self.collection = self.db[uuid.uuid4().hex]
        self.collection.create_index([('tema','text'),('resumen','text'),
            ('texto_usuario','text'),('texto_agente','text')],default_language='spanish')
        for i, text in enumerate(('índice reparación exacta', 'índice sin cambios',
                                  'índice reparacion pendiente', 'worker running code')):
            self.collection.insert_one({'turn_id':str(i),'version':1,'tema':text,
                'resumen':'','texto_usuario':text,'texto_agente':'','ruta_origen':'/synthetic'})

    def ids(self, term, expanded=True):
        return {r['turn_id'] for r in buscar(term,coleccion=self.collection,
                    expand_accents=expanded)['resultados']}

    def test_recovery_negation_phrase_and_default_unchanged(self):
        self.assertEqual(self.ids('reparacion',False),{'2'})
        self.assertEqual(self.ids('reparacion'),{'0','2'})
        self.assertEqual(self.ids('índice -reparacion'),{'1'})
        self.assertEqual(self.ids('"reparación exacta"'),{'0'})
        self.assertEqual(self.ids('"reparacion exacta"'),self.ids('"reparacion exacta"',False))
        self.assertEqual(self.ids('worker'),{'3'})
        self.assertEqual(self.ids('-reparacion'),set())

    def test_analysis_consumer_preserves_currency_and_limit(self):
        self.collection.insert_one({'turn_id':'0','version':2,'tema':'retirado',
            'resumen':'','texto_usuario':'','texto_agente':'','ruta_origen':'/synthetic'})
        result=query('reparacion',coleccion=self.collection,with_evidence=False,
                     expand_accents=True)
        self.assertEqual({r['turn_id'] for r in result['resultados']},{'2'})
        result=buscar('reparacion',coleccion=self.collection,expand_accents=True,max_resultados=1)
        self.assertEqual(len(result['resultados']),1)
        self.assertEqual(result['excluidos']['por_limite'],1)
