"""El gate de publicación distingue éxito efectivo de pruebas no ejecutadas."""
import importlib.util
import io
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('isolated_runner',
    Path(__file__).resolve().parents[1] / 'scripts' / 'run_isolated_tests.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PublicationGateTests(unittest.TestCase):
    def test_positive_skipped_empty_failed_and_expected_failure(self):
        for kind in ('positive', 'skip', 'fail', 'expected'):
            def probe(case, mode=kind):
                if mode == 'skip':
                    case.skipTest('prerrequisito sintético ausente')
                if mode in ('fail', 'expected'):
                    case.fail('fallo sintético')
            if kind == 'expected':
                probe = unittest.expectedFailure(probe)
            case = type('SyntheticCase', (unittest.TestCase,), {'test_probe': probe})
            result = unittest.TextTestRunner(stream=io.StringIO()).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(case))
            self.assertEqual(runner.publication_exit_code(result), int(kind != 'positive'))
        empty = unittest.TestResult()
        self.assertEqual(runner.publication_exit_code(empty), 1)

    def test_database_boundary(self):
        for allowed in ('admin', 'skopos_test_sources_123'):
            runner.check_database(allowed)
        for denied in ('skopos', '', 'other'):
            with self.assertRaisesRegex(RuntimeError, 'non_test_database_blocked'):
                runner.check_database(denied)
