#!/usr/bin/env python3
"""Mide el solapamiento léxico consulta→objetivo (métrica de reapertura del hito 11).

La hoja de ruta fija la condición para reabrir la búsqueda semántica:
cuántas consultas reales **no comparten ninguna palabra** con su objetivo —
lo único que un índice léxico no puede recuperar. Este instrumento computa
esa tasa sobre pares adjudicados (consulta real + objetivo adjudicado por el
Operador). Sólo lectura: no toca índices ni datos.

Entrada: JSONL con objetos {"query": "...", "target_turn_id": "..."} —el
texto objetivo se lee de `skopos.turnos` (unión de texto_usuario y
texto_agente, que es lo que indexa $text)— o {"query": "...",
"target_text": "..."} para pares autocontenidos.

Salida: informe JSON con detalle por par y resumen en dos variantes —
conteo sobre todas las palabras y sobre palabras de contenido (stopwords
españolas integradas, versión fijada abajo)— para que la decisión no dependa
de una lista discutible. Un par con cero palabras compartidas en la variante
de contenido es irrecuperable para el índice léxico vigente.

Uso:
  python3 scripts/lexical_overlap.py --pairs pares.jsonl [--self-check]
  python3 scripts/lexical_overlap.py --pairs pares.jsonl --database skopos
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# Stopwords españolas de alta frecuencia; versión fijada y reportada.
STOPWORDS_V1 = frozenset("""
a al algo alguna algunas alguno algunos ante antes como con contra cual cuando
de del desde donde dos el ella ellas ellos en entre era eran es esa esas ese
eso esos esta estaba están está están ese hecho hasta hay hoy la las le les lo
los más mi mis mucho muchos muy nada ni no nos nosotros nuestra nuestro o os
otra otras otro otros para pero poco por porque que quien se sea según ser si
sí sin sobre solo también tanto te tiene tienen todo todos tu tus un una uno
unos usted ustedes ya yo
""".split())

TOKEN_RE = re.compile(r"[a-záéíóúüñ0-9]+")


def tokenize(text):
    """Tokens léxicos en minúscula; la puntuación se descarta."""
    return TOKEN_RE.findall((text or "").casefold())


def content_terms(text):
    return [term for term in tokenize(text) if term not in STOPWORDS_V1]


def overlap(query, target):
    """Palabras compartidas consulta→objetivo, en dos variantes.

    Devuelve (compartidas_totales, compartidas_de_contenido,
    términos_de_consulta). Un índice $text con OR recupera si algún término
    casa; cero compartidas de contenido es la señal de irrecuperable.
    """
    query_terms = set(tokenize(query))
    target_terms = set(tokenize(target))
    shared_all = sorted(query_terms & target_terms)
    shared_content = sorted(
        term for term in shared_all if term not in STOPWORDS_V1)
    return shared_all, shared_content, sorted(query_terms)


def measure_pair(pair):
    """Mide un par; exige query y algún objetivo (texto o turn_id a resolver)."""
    if type(pair) is not dict or not pair.get('query'):
        raise ValueError('invalid_pair')
    target_text = pair.get('target_text')
    if target_text is None:
        if not pair.get('target_turn_id'):
            raise ValueError('invalid_pair')
        return None  # El texto se resuelve contra Mongo en la corrida real.
    shared_all, shared_content, query_terms = overlap(pair['query'], target_text)
    return {'query': pair['query'], 'target_text': target_text,
            'query_terms': query_terms,
            'shared_all': shared_all, 'shared_content': shared_content,
            'zero_overlap_all': not shared_all,
            'zero_overlap_content': not shared_content}


def summarize(details):
    total = len(details)
    zero_all = sum(1 for item in details if item['zero_overlap_all'])
    zero_content = sum(1 for item in details if item['zero_overlap_content'])
    return {'pairs': total,
            'zero_overlap_all': zero_all,
            'zero_overlap_all_rate': round(zero_all / total, 4) if total else None,
            'zero_overlap_content': zero_content,
            'zero_overlap_content_rate': round(zero_content / total, 4) if total else None,
            'stopwords': 'spanish-builtin-v1 (%d términos)' % len(STOPWORDS_V1),
            'irrecoverable_pairs': [item['query'] for item in details
                                    if item['zero_overlap_content']]}


def self_check():
    """Autocomprobación de la parte pura; sin Mongo ni archivos."""
    cases = [
        # (consulta, objetivo, compartidas totales esperadas, de contenido)
        ('¿Cómo se planea el respaldo?', 'El respaldo se planea diario a las once',
         ['el', 'planea', 'respaldo', 'se'], ['planea', 'respaldo']),
        ('respaldo planificado', 'El respaldo se planea diario a las once',
         ['respaldo'], ['respaldo']),
        ('copia de seguridad', 'respaldo de la noche',
         ['de'], []),  # sólo stopword: irrecuperable en contenido
        ('backups', 'El respaldo se planea diario a las once', [], []),
    ]
    for query, target, expected_all, expected_content in cases:
        shared_all, shared_content, _ = overlap(query, target)
        assert shared_all == expected_all, (query, shared_all)
        assert shared_content == expected_content, (query, shared_content)
    measured = measure_pair({'query': 'backups', 'target_text': 'respaldo diario'})
    assert measured['zero_overlap_content'] and measured['zero_overlap_all']
    measured = measure_pair({'query': 'respaldo', 'target_turn_id': 'turno-1'})
    assert measured is None  # turn_id pendiente de resolver: no inventa texto
    summary = summarize([measure_pair({'query': q, 'target_text': t})
                         for q, t, _, _ in cases])
    assert summary['pairs'] == 4 and summary['zero_overlap_content'] == 2
    assert summary['zero_overlap_all'] == 1
    for invalid in ({'target_text': 'sin consulta'}, {'query': 'respaldo'}):
        try:
            measure_pair(invalid)
            raise AssertionError('debió rechazar el par inválido: %r' % invalid)
        except ValueError as error:
            assert str(error) == 'invalid_pair'
    print('self-check OK — %d stopwords, métrica y resumen verificados'
          % len(STOPWORDS_V1))


def load_pairs(path):
    pairs = []
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))
    return pairs


def resolve_targets(pairs, uri, database):
    """Resuelve target_turn_id contra skopos.turnos; sólo lectura."""
    from pymongo import MongoClient
    with MongoClient(uri, serverSelectionTimeoutMS=3000) as client:
        turns = client[database].turnos
        for pair in pairs:
            if pair.get('target_text') is None:
                document = turns.find_one({'turn_id': pair['target_turn_id']},
                                          {'texto_usuario': 1, 'texto_agente': 1})
                if document is None:
                    raise ValueError('target_turn_id_not_found: %s'
                                     % pair['target_turn_id'])
                pair['target_text'] = '\n'.join(
                    filter(None, (document.get('texto_usuario'),
                                  document.get('texto_agente'))))
    return pairs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--pairs', help='JSONL de pares adjudicados')
    parser.add_argument('--database', default='skopos')
    parser.add_argument('--uri', default='mongodb://localhost:27017')
    parser.add_argument('--self-check', action='store_true',
                        help='autocomprobación de la parte pura; sin Mongo')
    args = parser.parse_args(argv)
    if args.self_check:
        self_check()
        return 0
    if not args.pairs:
        parser.error('--pairs es obligatorio salvo con --self-check.')
    try:
        pairs = load_pairs(args.pairs)
        pairs = resolve_targets(pairs, args.uri, args.database)
        details = [measure_pair(pair) for pair in pairs]
        report = {'summary': summarize(details),
                  'details': [{k: v for k, v in item.items() if k != 'target_text'}
                              for item in details]}
    except (OSError, ValueError) as error:
        print('error: %s' % error, file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
