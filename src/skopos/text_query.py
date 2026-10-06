"""Expansión optativa y conservadora de -cion para consultas léxicas."""
import re

TOKEN = re.compile(r'"[^"]*"|[^\s"]+')
WORD = re.compile(r'(-?)([a-zA-Z]+cion)', re.IGNORECASE | re.ASCII)


def expand_accents(query):
    """Añade variantes sin sustituir términos, frases ni identificadores.

    No es corrector ortográfico general. Comillas desbalanceadas o escapes
    quedan intactos: no inventar la interpretación de una gramática ambigua.
    Una variante negativa conserva el signo; nunca se convierte en OR positivo.
    """
    if '\\' in query or query.count('"') % 2:
        return query
    def replace(match):
        token = match.group()
        if ((match.start() and not query[match.start()-1].isspace())
                or (match.end() < len(query) and not query[match.end()].isspace())):
            return token
        word = WORD.fullmatch(token)
        if not word:
            return token
        sign, text = word.groups()
        accent = 'Ó' if text[-2].isupper() else 'ó'
        variant = sign + text[:-2] + accent + text[-1]
        return token + ' ' + variant
    return TOKEN.sub(replace, query)
