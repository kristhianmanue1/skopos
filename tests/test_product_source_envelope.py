"""Misma batería contractual aplicada al constructor integrado, no sólo al prototipo."""
from test_source_envelope import SourceEnvelopeTests as ExperimentalContract
from skopos.source_envelope import build_envelope


class ProductEnvelopeTests(ExperimentalContract):
    def build(self, raw=None, **overrides):
        arguments = {'project_id': 'project-a', 'source_id': 'meeting-1',
                     'captured_at': '2026-10-05T18:00:00-06:00'}
        arguments.update(overrides)
        return build_envelope(self.raw if raw is None else raw, **arguments)


# Evitar que unittest descubra otra copia de la clase importada.
del ExperimentalContract
