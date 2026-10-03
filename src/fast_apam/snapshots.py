"""Legacy filenames exist only at the import/export compatibility boundary."""
import csv
import io
import json
from datetime import date
from pathlib import Path
from .storage import sha

PREFIX='MSFT_IT_Historical_Combined_Pilot_'
SPECS=['Operating_Company_Metric_to_Factor_Mapping.md','Fast_APAM_Scoring_and_Status_Specification.md','Fast_APAM_Metric_Dictionary.md','Fast_APAM_Provisional_Normalization_and_Thresholds.md','Microsoft_Dated_GICS_and_Peer_Hierarchy_Decision.md','Data_Contract.md','Period_Construction_Rules.md','Decision_Register.md']
REFERENCES=['Research_Pilot_Output','Operating_Company_Factor_Input_Detailed_Audit','Source_Lineage_Catalog','Research_Pilot_Status_Audit','Research_Pilot_Vintage_Parent_Audit','Provisional_Factor_Score_Matrix']


def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def safe_name(name):
    if not name or name.startswith('/') or Path(name).is_absolute() or '..' in Path(name).parts or ':' in name or '\\' in name:
        raise ValueError('Unsafe artifact name: '+name)
    return name


def required(day):
    files=[f'MSFT_IT_Sector_Extraction_Batch_{day}_R1.csv',f'MSFT_IT_SEC_Filing_Index_{day}_R2.csv']
    for wave,revision in [('Wave1',3),('Wave2',4)]:
        files += [f'MSFT_IT_Historical_{wave}_{kind}_{day}_R1.csv' for kind in ['TTM_YoY_Observations','TTM_YoY_Audit','Canonical_Selected_Facts']]
        files.append(f'MSFT_IT_Historical_{wave}_Standalone_Quarters_{day}_R{revision}.csv')
    files += [f'MSFT_IT_Historical_Wave1_Operating_Company_{kind}_{day}_R1.csv' for kind in ['Factor_Input_Matrix','Factor_Coverage_Audit']]
    return files+SPECS+[f'Fast_APAM_Research_Pilot_Convention_001_{day}_R1.json']


def import_source(store, day, source):
    day=date.fromisoformat(day).isoformat()
    source=Path(source).resolve()
    files={}
    for name in required(day):
        path=source/name
        if not path.is_file():raise ValueError('Required prepared input missing: '+name)
        data=path.read_bytes()
        if name.endswith('.csv'):
            data_rows=rows(data)
            if not data_rows:raise ValueError('Empty required input: '+name)
            if any('model_date' in r and r['model_date']!=day for r in data_rows):
                raise ValueError('Input date mismatch: '+name)
        files['input',name]=data
    roster_name=f'MSFT_IT_Sector_Extraction_Batch_{day}_R1.csv'
    roster=rows(files['input',roster_name])
    members={r['ticker'] for r in roster}
    if len(members)!=len(roster):raise ValueError('Duplicate roster issuer')
    wave_members={wave:{r['ticker'] for r in rows(files['input',f'MSFT_IT_Historical_{wave}_TTM_YoY_Audit_{day}_R1.csv'])} for wave in ['Wave1','Wave2']}
    if wave_members['Wave1'] & wave_members['Wave2'] or set.union(*wave_members.values())!=members:
        raise ValueError('Wave membership does not reconcile to roster')
    filing_rows=rows(files['input',f'MSFT_IT_SEC_Filing_Index_{day}_R2.csv'])
    if any(r['eligible_on_model_date']=='Y' and (not r['model_available_date'] or r['model_available_date']>day) for r in filing_rows):
        raise ValueError('Eligible filing violates cutoff')
    for wave in wave_members:
        obs=rows(files['input',f'MSFT_IT_Historical_{wave}_TTM_YoY_Observations_{day}_R1.csv'])
        if any(r['signal_model_available_date']>day or r['ttm_rollforward_status']=='FAIL' for r in obs):
            raise ValueError('Observation availability or rollforward failure')
    policy=json.loads(files['input',f'Fast_APAM_Research_Pilot_Convention_001_{day}_R1.json'])
    if policy['model_date']!=day:raise ValueError('Policy date mismatch')
    exceptions=source/'Dated_Input_Exceptions.json'
    files['input',exceptions.name]=exceptions.read_bytes() if exceptions.exists() else b'{}'
    review=source/'Dated_Cohort_Review.json'
    if review.exists():
        data=json.loads(review.read_text())
        if data['model_date']!=day or data['status']!='PASS' or data['roster_sha256']!=sha(files['input',roster_name]):
            raise ValueError('Dated cohort review does not match roster')
        if not data.get('evidence_files'):raise ValueError('Missing cohort evidence')
        for name,digest in data['evidence_files'].items():
            path=(source/safe_name(name)).resolve()
            if not path.is_relative_to(source):raise ValueError('Cohort evidence escapes source folder')
            payload=path.read_bytes()
            if sha(payload)!=digest:raise ValueError('Cohort evidence checksum mismatch')
            files['input',name]=payload
        files['input',review.name]=review.read_bytes()
    else:
        # Import of the existing historical research pilot preserves its own
        # governing decision documents; it does not fabricate a newer review.
        files['input','Historical_Cohort_Import.json']=json.dumps({'model_date':day,'scope':'Imported historical research snapshot governed by its preserved decision register; no new universe approval.'}).encode()
    for kind in REFERENCES:
        name=PREFIX+kind+f'_{day}_R1.csv'
        if (source/name).exists():files['reference',name]=(source/name).read_bytes()
    config={'model_date':day,'cohort_size':len(roster),'wave_counts':{w:len(v) for w,v in wave_members.items()},'scope':'Information Technology operating-company research pilot','production_approved':False}
    fingerprint=store.import_snapshot(day,config,files)
    return {'model_date':day,'fingerprint':fingerprint,'input_files':sum(r=='input' for r,n in files),'reference_files':sum(r=='reference' for r,n in files),'source_bytes':sum(len(v) for v in files.values()),'cohort_size':len(roster)}
