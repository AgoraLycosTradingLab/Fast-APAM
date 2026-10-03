"""Immutable snapshots and deduplicated, compressed artifacts in SQLite."""
import hashlib
import json
import sqlite3
import zlib
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS blobs(hash TEXT PRIMARY KEY, original_bytes INTEGER NOT NULL, payload BLOB NOT NULL);
          CREATE TABLE IF NOT EXISTS snapshots(date TEXT PRIMARY KEY, config TEXT NOT NULL, fingerprint TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS artifacts(date TEXT NOT NULL REFERENCES snapshots(date), name TEXT NOT NULL, role TEXT NOT NULL, hash TEXT NOT NULL REFERENCES blobs(hash), PRIMARY KEY(date,name,role));
          CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, date TEXT NOT NULL REFERENCES snapshots(date), summary TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS outputs(run_id TEXT NOT NULL REFERENCES runs(id), name TEXT NOT NULL, hash TEXT NOT NULL REFERENCES blobs(hash), PRIMARY KEY(run_id,name));
        ''')

    def close(self):
        self.db.close()

    def put(self, data):
        digest = sha(data)
        self.db.execute('INSERT OR IGNORE INTO blobs VALUES (?,?,?)', (digest, len(data), zlib.compress(data, 6)))
        return digest

    def get(self, digest):
        row = self.db.execute('SELECT payload FROM blobs WHERE hash=?', (digest,)).fetchone()
        if row is None:
            raise ValueError('Missing artifact: '+digest)
        data = zlib.decompress(row[0])
        if sha(data) != digest:
            raise ValueError('Artifact checksum mismatch: '+digest)
        return data

    def import_snapshot(self, day, config, files):
        manifest = {role+'/'+name: sha(data) for (role, name), data in files.items()}
        fingerprint = sha(json.dumps({'config':config,'files':manifest},sort_keys=True).encode())
        existing = self.db.execute('SELECT fingerprint FROM snapshots WHERE date=?', (day,)).fetchone()
        if existing:
            if existing[0] != fingerprint:
                raise ValueError('Snapshot already exists with different inputs; use a separate store for a revision')
            return fingerprint
        with self.db:
            self.db.execute('INSERT INTO snapshots VALUES (?,?,?)',(day,json.dumps(config,sort_keys=True),fingerprint))
            for (role,name),data in files.items():
                self.db.execute('INSERT INTO artifacts VALUES (?,?,?,?)',(day,name,role,self.put(data)))
        return fingerprint

    def snapshot(self, day):
        row = self.db.execute('SELECT config,fingerprint FROM snapshots WHERE date=?',(day,)).fetchone()
        if row is None:
            raise ValueError('Import a validated source snapshot for '+day+' first')
        config=json.loads(row[0])
        manifest={role+'/'+name:digest for name,role,digest in self.db.execute('SELECT name,role,hash FROM artifacts WHERE date=?',(day,)).fetchall()}
        actual=sha(json.dumps({'config':config,'files':manifest},sort_keys=True).encode())
        if actual!=row[1] or config.get('model_date')!=day:
            raise ValueError('Snapshot metadata fingerprint mismatch')
        return config,row[1]

    def files(self, day, role='input'):
        return {name:self.get(digest) for name,digest in self.db.execute('SELECT name,hash FROM artifacts WHERE date=? AND role=? ORDER BY name',(day,role)).fetchall()}

    def save_run(self, run_id, day, summary, outputs):
        with self.db:
            self.db.execute('INSERT INTO runs VALUES (?,?,?)',(run_id,day,json.dumps(summary,sort_keys=True)))
            for name,data in outputs.items():
                self.db.execute('INSERT INTO outputs VALUES (?,?,?)',(run_id,name,self.put(data)))

    def run_files(self, run_id):
        return {name:self.get(digest) for name,digest in self.db.execute('SELECT name,hash FROM outputs WHERE run_id=? ORDER BY name',(run_id,)).fetchall()}
