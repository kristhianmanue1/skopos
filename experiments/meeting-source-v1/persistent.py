"""Persistencia SQLite del piloto; no cambia el almacén Mongo de Skopos."""
import json
from pathlib import Path
import sqlite3

from pilot import MeetingStore

APPLICATION_ID = 0x534B4D31
SCHEMA_VERSION = 1


class PersistentMeetingStore(MeetingStore):
    """Transacciones serializan importaciones; copias de fuente siguen externas."""
    def __init__(self, database):
        path = Path(database)
        existed = path.exists()
        self.connection = sqlite3.connect(str(path), timeout=5, isolation_level=None)
        try:
            self.connection.execute('PRAGMA synchronous=FULL')
            self.connection.execute('BEGIN IMMEDIATE')
            app = self.connection.execute('PRAGMA application_id').fetchone()[0]
            version = self.connection.execute('PRAGMA user_version').fetchone()[0]
            if existed:
                if app != APPLICATION_ID or version != SCHEMA_VERSION:
                    raise ValueError('unsupported_pilot_database')
                self.connection.execute('SELECT source_id, revision, record FROM sources LIMIT 0')
            else:
                self.connection.execute('CREATE TABLE sources (source_id TEXT NOT NULL, revision INTEGER NOT NULL, record TEXT NOT NULL, PRIMARY KEY(source_id, revision))')
                self.connection.execute('PRAGMA application_id=%d' % APPLICATION_ID)
                self.connection.execute('PRAGMA user_version=%d' % SCHEMA_VERSION)
            self.connection.commit()
            self.sources = {}
        except Exception:
            self.connection.rollback()
            self.connection.close()
            raise

    def _load(self):
        sources = {}
        for identity, revision, raw in self.connection.execute('SELECT source_id, revision, record FROM sources ORDER BY source_id, revision'):
            record = json.loads(raw)
            if record['value']['source_id'] != identity or record['value']['revision'] != revision:
                raise ValueError('stored_identity_mismatch')
            sources.setdefault(identity, {})[revision] = record
        self.sources = sources

    def ingest(self, path):
        self.connection.execute('BEGIN IMMEDIATE')
        try:
            self._load()
            before = {(identity, revision) for identity, versions in self.sources.items() for revision in versions}
            status = super().ingest(path)
            for identity, versions in self.sources.items():
                for revision, record in versions.items():
                    if (identity, revision) not in before:
                        self.connection.execute('INSERT INTO sources VALUES (?, ?, ?)',
                            (identity, revision, json.dumps(record, ensure_ascii=False)))
            self.connection.commit()
            return status
        except Exception:
            self.connection.rollback()
            raise

    def search(self, term):
        self._load()
        return super().search(term)

    def fetch(self, source_id, revision, segment_id):
        self._load()
        return super().fetch(source_id, revision, segment_id)

    def close(self):
        self.connection.close()
