"""Regresión de vigencia contra Mongo real, en una base efímera exclusiva."""
import unittest
import uuid

from test_almacenamiento import _mongo_disponible
from skopos.almacenamiento import buscar_por_tema, coleccion_local


@unittest.skipUnless(_mongo_disponible(), "Mongo local no disponible")
class CurrentRevisionTests(unittest.TestCase):
    def setUp(self):
        database = "skopos_test_currency_" + uuid.uuid4().hex
        self.collection = coleccion_local(db=database)
        client = self.collection.database.client
        self.addCleanup(client.close)
        self.addCleanup(client.drop_database, database)

    def add(self, identity, version, text, project="current"):
        document = {"turn_id": identity, "tema": text, "resumen": text,
                    "proyecto": project}
        if version is not None:
            document["version"] = version
        self.collection.insert_one(document)

    def test_old_match_without_current_match_is_excluded(self):
        self.add("source", 1, "zeppelin")
        self.add("source", 2, "corrected")
        self.assertEqual(buscar_por_tema("zeppelin", coleccion=self.collection), [])

    def test_current_match_is_returned_as_positive_control(self):
        self.add("source", 1, "old")
        self.add("source", 2, "zeppelin")
        result = buscar_por_tema("zeppelin", coleccion=self.collection)
        self.assertEqual([(d["turn_id"], d["version"]) for d in result], [("source", 2)])

    def test_project_filter_does_not_resurrect_an_old_revision(self):
        self.add("source", 1, "zeppelin", "old-project")
        self.add("source", 2, "zeppelin", "new-project")
        self.assertEqual(buscar_por_tema("zeppelin", coleccion=self.collection,
                                        proyecto="old-project"), [])

    def test_legacy_and_unrelated_identities(self):
        self.add("legacy", None, "zeppelin")
        self.add("other", 8, "zeppelin")
        result = buscar_por_tema("zeppelin", coleccion=self.collection)
        self.assertEqual({d["turn_id"] for d in result}, {"legacy", "other"})
        self.add("legacy", 1, "corrected")
        result = buscar_por_tema("zeppelin", coleccion=self.collection)
        self.assertEqual([d["turn_id"] for d in result], ["other"])

    def test_matching_revisions_do_not_duplicate_results(self):
        self.add("source", 1, "zeppelin")
        self.add("source", 2, "zeppelin")
        result = buscar_por_tema("zeppelin", coleccion=self.collection)
        self.assertEqual([d["version"] for d in result], [2])
