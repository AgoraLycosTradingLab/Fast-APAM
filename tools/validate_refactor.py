"""Run portable tests plus exact comparisons for every imported reference snapshot."""
import argparse
import io
import json
import sys
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fast_apam.storage import Store
from fast_apam.runner import calculate,verify_outputs,code_fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',type=Path,default=ROOT/'data'/'fast_apam.sqlite')
    args=parser.parse_args()
    log=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(stream=log,verbosity=1).run(suite)
    if not result.wasSuccessful():
        print(log.getvalue());return 1
    store=Store(args.store)
    try:
        dates=[r[0] for r in store.db.execute('SELECT date FROM snapshots ORDER BY date')]
        if not dates:raise ValueError('Import the reference snapshots before regression validation')
        checks=[];timings=[]
        for day in dates:
            started=time.perf_counter()
            run_id,summary,outputs=calculate(store,day,force=True)
            cold=time.perf_counter()-started
            comparison=verify_outputs(store,day,outputs)
            checks.append(comparison)
            started=time.perf_counter()
            _,cached,cached_outputs=calculate(store,day)
            warm=time.perf_counter()-started
            if outputs!=cached_outputs or not cached['cache_hit']:raise ValueError('Cache output changed')
            timings.append({'model_date':day,'full_calculation_wall_seconds':round(cold,4),'cached_wall_seconds':round(warm,4),'cached_results_identical':True,'run_id':run_id})
        report={'passed':result.wasSuccessful() and all(x['passed'] for x in checks),'portable_unit_tests':result.testsRun,'unit_failures':len(result.failures),'unit_errors':len(result.errors),'unit_skipped':len(result.skipped),'code_fingerprint':code_fingerprint(),'snapshot_comparisons':checks}
        (ROOT/'docs'/'refactor-validation.json').write_text(json.dumps(report,indent=2))
        logical=store.db.execute('SELECT SUM(original_bytes) FROM blobs').fetchone()[0]
        stats={'timings':timings,'sqlite_bytes':args.store.stat().st_size,'distinct_stored_artifact_uncompressed_bytes':logical,'stored_blob_count':store.db.execute('SELECT COUNT(*) FROM blobs').fetchone()[0],
               'compression_reduction_percent':round((1-args.store.stat().st_size/logical)*100,2),'routine_files_per_run':3,
               'scope':'Prepared snapshots and derived artifacts only. Raw historical source archives remain separate. Timing includes local execution and storage; these are single-machine measurements, not service guarantees.'}
        (ROOT/'docs'/'benchmark.json').write_text(json.dumps(stats,indent=2))
        print(json.dumps({'passed':report['passed'],'unit_tests':result.testsRun,'dates':dates,'table_comparisons':sum(len(x['checks']) for x in checks),'benchmark':stats},indent=2))
        return 0 if report['passed'] else 1
    finally:store.close()


if __name__=='__main__':raise SystemExit(main())
