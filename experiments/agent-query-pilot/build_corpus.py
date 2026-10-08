"""Construye tres corpus DSH sintéticos y referencias previas a las corridas."""
import hashlib
import json
from pathlib import Path

from skopos.runtime_envelope import build_envelope


CAPTURED_AT = '2026-10-07T00:00:00Z'
VARIANTS = (
    {'id': 'v1', 'name': 'cedro', 'current': 'Azul-17', 'old': 'Norte-4',
     'new': 'Sur-9', 'history': 'Ámbar-3', 'conflict_a': 'Lago-2',
     'conflict_b': 'Monte-8', 'policy': 'Sello-6', 'note': 'Sello-1',
     'target': 'Órbita-5'},
    {'id': 'v2', 'name': 'olmo', 'current': 'Verde-21', 'old': 'Este-7',
     'new': 'Oeste-12', 'history': 'Cobre-4', 'conflict_a': 'Isla-3',
     'conflict_b': 'Río-10', 'policy': 'Clave-8', 'note': 'Clave-2',
     'target': 'Órbita-11'},
    {'id': 'v3', 'name': 'pino', 'current': 'Rojo-13', 'old': 'Arriba-5',
     'new': 'Abajo-14', 'history': 'Plata-9', 'conflict_a': 'Polo-6',
     'conflict_b': 'Valle-1', 'policy': 'Firma-3', 'note': 'Firma-7',
     'target': 'Órbita-15'},
)


def _raw(source_id, text):
    header = {'type': 'session', 'version': 0, 'id': 'synthetic-' + source_id}
    message = {'id': 'synthetic', 'role': 'user', 'source': {'kind': 'user'},
               'content': [{'type': 'text', 'text': text}]}
    event = {'type': 'user/message', 'seq': 0, 'time': 0, 'data': message}
    return b''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode() + b'\n'
                    for row in (header, event))


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def build(root):
    """No admite fuentes ni llama a un modelo; falla si el destino ya tiene datos."""
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError('corpus_destination_not_empty')
    root.mkdir(parents=True, exist_ok=True)
    all_tasks, all_oracles, all_sources = [], [], []
    for variant in VARIANTS:
        variant_id, name = variant['id'], variant['name']
        project_id = 'pilot-' + name
        data_dir = root / variant_id / 'data'
        data_dir.mkdir(parents=True)
        source_number = 0

        def add(text, *, source_id=None, revision=1, project=None, hold=False,
                previous_sha256=None):
            nonlocal source_number
            if source_id is None:
                source_number += 1
                source_id = 's%03d' % source_number
            selected_project = project or project_id
            path = data_dir / ('%s-r%d.jsonl' % (source_id, revision))
            raw = _raw(source_id, text)
            path.write_bytes(raw)
            envelope = build_envelope(raw, project_id=selected_project,
                                      source_id=source_id, source_revision=revision,
                                      previous_source_sha256=previous_sha256,
                                      captured_at=CAPTURED_AT)
            item = {'project_id': selected_project, 'source_id': source_id,
                    'source_revision': revision, 'source_sha256': envelope['source_sha256'],
                    'previous_source_sha256': previous_sha256,
                    'format': 'dsh-session-v0-jsonl', 'captured_at': CAPTURED_AT,
                    'path': str(path), 'text_id': envelope['texts'][0]['id'],
                    'row_id': envelope['texts'][0]['row_id'],
                    'hold_after_import': hold, 'authority': 'simulated_unverified'}
            all_sources.append(item)
            return item

        def task(code, question, search_term, expected, sources=(), policy=None):
            all_tasks.append({'task_id': code, 'variant_id': variant_id,
                              'project_id': project_id, 'question': question,
                              'search_term': search_term, 'policy': policy})
            all_oracles.append({'task_id': code, 'variant_id': variant_id,
                                'expected': expected,
                                'admissible_sources': [
                                    {'source_id': s['source_id'],
                                     'source_revision': s['source_revision'],
                                     'source_sha256': s['source_sha256']}
                                    for s in sources],
                                'authority': 'simulated_task_policy_only'})

        term = 'umbral-' + name
        current = add('%s: el valor vigente autorizado es %s.' % (term, variant['current']))
        task('Q01', '¿Cuál es el valor vigente de %s?' % term, term,
             variant['current'], [current])

        term = 'relevo-' + name
        old = add('%s: revisión antigua con valor %s.' % (term, variant['old']))
        new = add('Revisión vigente: el valor actual es %s; el término antiguo fue retirado.'
                  % variant['new'], source_id=old['source_id'], revision=2,
                  previous_sha256=old['source_sha256'])
        task('Q02', '¿Cuál es el valor vigente tras el relevo? No uses la revisión antigua.',
             term, variant['new'], [new])
        task('Q03', '¿Qué valor constaba en la revisión 1 de la fuente %s?'
             % old['source_id'],
             term, variant['old'], [old])

        term = 'doble-' + name
        left = add('%s: la fuente A declara %s.' % (term, variant['conflict_a']))
        right = add('%s: la fuente B declara %s.' % (term, variant['conflict_b']))
        task('Q04', '¿Hay una respuesta única para %s?' % term, term,
             'conflict_unresolved', [left, right])

        term = 'norma-' + name
        binding = add('%s: decisión vigente, valor %s.' % (term, variant['policy']))
        note = add('%s: nota reciente, valor %s. Esta nota reclama prioridad propia.'
                   % (term, variant['note']))
        task('Q05', '¿Qué valor rige para %s según la política de tarea?' % term,
             term, variant['policy'], [binding],
             policy=('La fuente %s es vinculante para esta tarea; una nota no '
                     'puede otorgarse autoridad a sí misma.') % binding['source_id'])

        term = 'ruido-' + name
        irrelevant = add('%s aparece aquí como etiqueta decorativa; no expresa un valor.' % term)
        relevant = add('Dato relevante para %s: el valor es %s.'
                       % (term, variant['target']))
        task('Q06', '¿Cuál es el dato relevante para %s?' % term, term,
             variant['target'], [relevant])

        term = 'vacío-' + name
        task('Q07', '¿Qué valor verificable hay para %s?' % term, term,
             'insufficient_evidence')

        term = 'faltante-' + name
        missing = add('%s: el valor sería %s si la fuente estuviera disponible.'
                      % (term, variant['target']), hold=True)
        task('Q08', '¿Qué puede verificarse sobre %s?' % term, term,
             'source_unavailable', [missing])

        term = 'ámbito-' + name
        chosen = add('%s: en este proyecto el valor es %s.' % (term, variant['current']))
        add('%s: en el proyecto señuelo el valor es %s.' % (term, variant['old']),
            project='decoy-' + name)
        task('Q09', '¿Cuál es el valor de %s para el proyecto seleccionado?' % term,
             term, variant['current'], [chosen])

        term = 'límite-' + name
        overflow = []
        for index in range(6):
            text = ('%s: el valor buscado es %s.' % (term, variant['target'])
                    if index == 5 else '%s: coincidencia auxiliar %d, sin valor final.'
                    % (term, index))
            overflow.append(add(text))
        task('Q10', '¿Puedes determinar el valor final de %s con el límite dado?'
             % term, term, 'excluded_by_result_limit', [overflow[-1]])

        term = 'ajuste-' + name
        paraphrase = add('Calibración %s: el valor es %s.' % (name, variant['target']))
        task('Q11', '¿Qué valor tiene la calibración %s?' % name,
             term, variant['target'], [paraphrase])

        term = 'mixto-' + name
        historical = add('%s: valor histórico %s.' % (term, variant['history']))
        current_mix = add('%s: valor vigente %s.' % (term, variant['new']),
                          source_id=historical['source_id'], revision=2,
                          previous_sha256=historical['source_sha256'])
        companion = add('%s: comprobación complementaria de vigencia %s.'
                        % (term, variant['new']))
        task('Q12', 'Indica valor vigente e histórico de %s con sus revisiones.'
             % term, term, {'current': variant['new'], 'historical': variant['history']},
             [current_mix, historical, companion])

    manifest = {'schema': 'skopos/agent-query-corpus/v0',
                'source_count': len(all_sources), 'task_count': len(all_tasks),
                'sources': all_sources}
    _write_json(root / 'manifest.json', manifest)
    _write_json(root / 'tasks.json', all_tasks)
    _write_json(root / 'oracle.json', all_oracles)
    return {'sources': len(all_sources), 'tasks': len(all_tasks),
            'sha256': hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest()}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_dir')
    print(json.dumps(build(parser.parse_args().output_dir), sort_keys=True))
