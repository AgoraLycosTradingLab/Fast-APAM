"""Run prepared snapshots; preserve audits without exposing intermediate files."""
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from .storage import sha
from .snapshots import PREFIX,rows,safe_name


def code_fingerprint():
    root=Path(__file__).parent
    return sha(json.dumps({str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(root.rglob('*.py'))},sort_keys=True).encode())


def csv_bytes(values, fields=None):
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=fields or list(values[0]))
    writer.writeheader()
    writer.writerows(values)
    return stream.getvalue().encode('utf-8')


def verify_outputs(store, day, outputs):
    references=store.files(day,'reference')
    if not references:raise ValueError('No frozen reference outputs imported for '+day)
    checks=[]
    for name,payload in references.items():
        if name not in outputs:
            checks.append({'artifact':name,'passed':False,'reason':'OUTPUT_MISSING'})
            continue
        expected,actual=rows(payload),rows(outputs[name])
        differences=[]
        if len(expected)!=len(actual):differences.append({'expected_rows':len(expected),'actual_rows':len(actual)})
        for i,(a,b) in enumerate(zip(expected,actual),2):
            if a!=b:
                differences.append({'row':i,'columns':[k for k in set(a)|set(b) if a.get(k)!=b.get(k)]})
                if len(differences)>=10:break
        checks.append({'artifact':name,'passed':not differences,'rows':len(actual),'differences':differences})
    return {'model_date':day,'passed':all(x['passed'] for x in checks),'checks':checks}


def calculate(store,day,force=False):
    started=time.perf_counter()
    config,snapshot_fp=store.snapshot(day)
    code_fp=code_fingerprint()
    run_id=sha((snapshot_fp+code_fp).encode())
    cached=store.db.execute('SELECT summary FROM runs WHERE id=?',(run_id,)).fetchone()
    if cached and not force:
        outputs=store.run_files(run_id)
        summary=dict(json.loads(cached[0]),cache_hit=True,elapsed_seconds=round(time.perf_counter()-started,4))
        return run_id,summary,outputs
    inputs=store.files(day)
    with tempfile.TemporaryDirectory(prefix='fast_apam_') as temp:
        root=Path(temp)
        for name,payload in inputs.items():
            path=root/safe_name(name)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(payload)
        # Existing stage manifests hash implementation files beside their inputs.
        # Copies live only in this temporary compatibility workspace.
        for path in (Path(__file__).parent/'engine').glob('*.py'):
            shutil.copy2(path,root/path.name)
        cfg=root/'run_config.json'
        cfg.write_text(json.dumps(config))
        env=dict(os.environ,FAST_APAM_RUN_CONFIG=str(cfg),PYTHONDONTWRITEBYTECODE='1')
        source_root=str(Path(__file__).resolve().parents[1])
        env['PYTHONPATH']=source_root+os.pathsep+env.get('PYTHONPATH','')
        result=subprocess.run([sys.executable,'-m','fast_apam.worker',str(root)],env=env,text=True,capture_output=True)
        if result.returncode:
            raise RuntimeError('Calculation failed; no results published.\n'+result.stderr[-7000:])
        # Preserve code bytes named by stage checksum manifests as audit evidence.
        # They are deduplicated in SQLite and never copied into routine outputs.
        outputs={p.name:p.read_bytes() for p in root.iterdir() if p.is_file() and p.name not in inputs and p.suffix in {'.csv','.json','.py'}}
    summary=json.loads(outputs[PREFIX+'Research_Pilot_Run_Summary'+f'_{day}_R1.json'])
    summary.update(run_id=run_id,input_fingerprint=snapshot_fp,code_fingerprint=code_fp,cache_hit=False,elapsed_seconds=round(time.perf_counter()-started,4),status='COMPLETE')
    if cached:
        prior=store.run_files(run_id)
        if outputs!=prior:raise ValueError('Same input and code produced different outputs; original cached run preserved')
    else:store.save_run(run_id,day,summary,outputs)
    return run_id,summary,outputs


def publish(store,day,output,force=False,verify=False):
    destination=Path(output)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Output directory must be new or empty; existing results are never overwritten')
    run_id,summary,outputs=calculate(store,day,force)
    validation=verify_outputs(store,day,outputs) if verify else None
    if validation and not validation['passed']:
        raise ValueError('Reference regression failed: '+json.dumps(validation))
    result_name=PREFIX+'Research_Pilot_Output'+f'_{day}_R1.csv'
    result_rows=rows(outputs[result_name])
    held=[r for r in result_rows if r['score_published']!='YES']
    if validation:summary['reference_validation']=validation
    # A completed directory is promoted atomically after all outputs are written.
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='apam_publish_',dir=destination.parent) as temp:
        pending=Path(temp)/'ready'
        pending.mkdir()
        (pending/'results.csv').write_bytes(outputs[result_name])
        fields=['ticker','company_name','PROVISIONAL_DATA_STATUS','gate_reason','underlying_candidate_hold_reason']
        (pending/'exceptions.csv').write_bytes(csv_bytes([{k:r[k] for k in fields} for r in held],fields))
        summary['output_sha256']={'results.csv':sha((pending/'results.csv').read_bytes()),'exceptions.csv':sha((pending/'exceptions.csv').read_bytes())}
        (pending/'run.json').write_text(json.dumps(summary,indent=2))
        if destination.exists():destination.rmdir() # verified empty above; failure is safe if another process wrote it
        pending.rename(destination)
    return summary


def export_audit(store,run_id,output):
    result=store.db.execute('SELECT date,summary FROM runs WHERE id=?',(run_id,)).fetchone()
    if not result:raise ValueError('Unknown successful run ID')
    payloads=store.files(result[0])|store.run_files(run_id)
    payloads['run.json']=result[1].encode()
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,data in payloads.items():archive.writestr(safe_name(name),data)
    return {'run_id':run_id,'artifacts':len(payloads),'zip_bytes':path.stat().st_size}
