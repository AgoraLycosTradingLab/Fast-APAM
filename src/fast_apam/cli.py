import argparse
import csv
import json
import sys
from pathlib import Path
from .storage import Store
from .snapshots import import_source
from .runner import publish,calculate,verify_outputs,export_audit


def main():
    parser=argparse.ArgumentParser(description='Fast APAM: date-driven provisional research snapshots')
    parser.add_argument('--store',default='data/fast_apam.sqlite')
    commands=parser.add_subparsers(dest='command',required=True)
    imp=commands.add_parser('import-snapshot',help='Freeze prepared inputs; never download or silently relabel old data')
    imp.add_argument('--date',required=True);imp.add_argument('--source',required=True)
    run=commands.add_parser('run',help='Calculate or reuse an identical verified run')
    run.add_argument('--date',required=True);run.add_argument('--output',required=True)
    run.add_argument('--source',help='Import prepared inputs before calculating')
    run.add_argument('--verify',action='store_true',help='Require equality to the imported frozen reference tables')
    run.add_argument('--force',action='store_true',help='Recalculate and check determinism instead of using cache')
    verify=commands.add_parser('verify');verify.add_argument('--date',required=True)
    audit=commands.add_parser('export-audit');audit.add_argument('--run-id',required=True);audit.add_argument('--output',required=True)
    commands.add_parser('list')
    fetch=commands.add_parser('fetch-new-filings',help='Cache only missing SEC documents from a reviewed dated filing index')
    fetch.add_argument('--date',required=True);fetch.add_argument('--index',required=True)
    setup=commands.add_parser('check-setup',help='Check customer ticker-file syntax offline; does not approve a scoring universe')
    setup.add_argument('--date',required=True);setup.add_argument('--universe',required=True)
    prepare=commands.add_parser('prepare-data',help='Discover SEC issuers and acquire dated filing/fact candidates; does not score')
    prepare.add_argument('--date',required=True);prepare.add_argument('--universe',required=True)
    prepare.add_argument('--output',required=True)
    prepare.add_argument('--history-start',help='Earliest filing date; default January 1 three years before model date, minimum 2023-01-01')
    args=parser.parse_args()
    if args.command=='prepare-data':
        from .preparation import prepare
        try:
            result=prepare(args.universe,args.date,args.output,args.history_start,
                           progress=lambda message: print(message,file=sys.stderr,flush=True))
            print(json.dumps(result,indent=2))
            return 1 if result['status']=='INCOMPLETE' else 0
        except (ValueError,OSError,UnicodeError,csv.Error) as error:
            parser.exit(1,str(error)+'\n')
    if args.command=='check-setup':
        from .customer_setup import check_setup
        try:
            print(json.dumps(check_setup(args.universe,args.date),indent=2))
            return 0
        except (ValueError,OSError,UnicodeError,csv.Error) as error:
            parser.exit(1,str(error)+'\n')
    store=Store(args.store)
    try:
        if args.command=='import-snapshot':result=import_source(store,args.date,args.source)
        elif args.command=='run':
            if args.source:import_source(store,args.date,args.source)
            result=publish(store,args.date,args.output,args.force,args.verify)
        elif args.command=='verify':
            _,_,outputs=calculate(store,args.date)
            result=verify_outputs(store,args.date,outputs)
            if not result['passed']:
                print(json.dumps(result,indent=2));return 1
        elif args.command=='export-audit':result=export_audit(store,args.run_id,args.output)
        elif args.command=='fetch-new-filings':
            from .acquisition import fetch_new
            result=fetch_new(store,Path(args.index).read_bytes(),args.date)
            if result['failures']:
                print(json.dumps(result,indent=2));return 1
        else:result=[{'date':d,'fingerprint':f} for d,f in store.db.execute('SELECT date,fingerprint FROM snapshots ORDER BY date')]
        print(json.dumps(result,indent=2))
        return 0
    except (ValueError,RuntimeError,FileNotFoundError) as error:
        parser.exit(1,str(error)+'\n')
    finally:store.close()
