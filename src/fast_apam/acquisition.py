"""Incremental immutable SEC-document retrieval; does not approve accounting facts."""
import gzip
import time
from datetime import datetime,timezone
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from .snapshots import rows
from .credentials import sec_user_agent


def validate_url(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.netloc!='www.sec.gov' or not parsed.path.startswith('/Archives/edgar/data/') or parsed.query or parsed.fragment:
        raise ValueError('Only immutable SEC EDGAR document URLs are accepted')


def download(url, user_agent):
    request=Request(url,headers={'User-Agent':user_agent,'Accept-Encoding':'gzip'})
    with urlopen(request,timeout=60) as response:
        data=response.read()
        if response.headers.get('Content-Encoding')=='gzip':data=gzip.decompress(data)
        return data


def fetch_new(store,index_data,day,transport=download,delay=.15):
    index=rows(index_data)
    if any(r.get('model_date')!=day for r in index):raise ValueError('Filing index date mismatch')
    selected={}
    for r in index:
        if r['eligible_on_model_date']!='Y':continue
        if not r['model_available_date'] or r['model_available_date']>day:raise ValueError('Filing is not available at the requested cutoff')
        validate_url(r['source_url'])
        selected[r['source_url']]=r
    store.db.execute('CREATE TABLE IF NOT EXISTS documents(url TEXT PRIMARY KEY, accession TEXT NOT NULL, hash TEXT NOT NULL REFERENCES blobs(hash), retrieved_utc TEXT NOT NULL)')
    saved,reused,failures=[],[],[]
    agent=None
    for url,r in selected.items():
        cached=store.db.execute('SELECT hash FROM documents WHERE url=?',(url,)).fetchone()
        if cached:
            store.get(cached[0]) # Verify cached bytes before trusting the retrieval.
            reused.append(r['accession_number']);continue
        if agent is None:agent=sec_user_agent()
        try:
            data=transport(url,agent)
            if not data:raise ValueError('Empty SEC response')
            with store.db:
                digest=store.put(data)
                store.db.execute('INSERT INTO documents VALUES (?,?,?,?)',(url,r['accession_number'],digest,datetime.now(timezone.utc).isoformat()))
            saved.append(r['accession_number'])
        except Exception as error:
            failures.append({'accession':r['accession_number'],'error':type(error).__name__})
        if delay:time.sleep(delay)
    return {'model_date':day,'downloaded':len(saved),'cache_hits':len(reused),'failures':failures,'status':'COMPLETE' if not failures else 'INCOMPLETE','scoring_inputs_approved':False}
