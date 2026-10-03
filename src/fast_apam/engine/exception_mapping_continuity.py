"""Build point-in-time continuity evidence for approved exception mappings."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path
MAPPINGS = {'GLW': {'cik': '0000024741', 'canonical_concept': 'capital_expenditures', 'rule_id': 'CAPEX-GLW-001', 'components': ('PaymentsForCapitalImprovements',)}, 'IT': {'cik': '0000749251', 'canonical_concept': 'capital_expenditures', 'rule_id': 'CAPEX-IT-001', 'components': ('PaymentsForCapitalImprovements',)}, 'ROP': {'cik': '0000882835', 'canonical_concept': 'capital_expenditures', 'rule_id': 'CAPEX-ROP-001', 'components': ('PaymentsToAcquireOtherProductiveAssets', 'PaymentsToDevelopSoftware')}}

def build(index_path: Path, cache_dir: Path, evidence_path: Path, summary_path: Path) -> tuple[list[dict], list[dict]]:
    with index_path.open(newline='', encoding='utf-8-sig') as handle:
        filing_rows = list(csv.DictReader(handle))
    eligible_by_ticker = {ticker: {row['accession_number'] for row in filing_rows if row['ticker'] == ticker and row['eligible_on_model_date'] == 'Y'} for ticker in MAPPINGS}
    evidence = []
    summaries = []
    for ticker, spec in MAPPINGS.items():
        with gzip.open(cache_dir / f"CIK{spec['cik']}.json.gz", 'rb') as handle:
            payload = json.load(handle)
        by_period: dict[tuple, dict[str, int | float]] = defaultdict(dict)
        metadata: dict[tuple, dict] = {}
        for component in spec['components']:
            block = payload.get('facts', {}).get('us-gaap', {}).get(component, {})
            for unit, observations in block.get('units', {}).items():
                if unit != 'USD':
                    continue
                for observation in observations:
                    if observation.get('accn') not in eligible_by_ticker[ticker]:
                        continue
                    key = (observation.get('accn', ''), observation.get('start', ''), observation.get('end', ''))
                    by_period[key][component] = observation.get('val')
                    metadata[key] = observation
        complete_periods = set()
        for key, values in sorted(by_period.items(), key=lambda item: (item[0][2], item[0][0], item[0][1])):
            missing = [component for component in spec['components'] if component not in values]
            complete = not missing
            if complete:
                complete_periods.add((key[1], key[2]))
            total = sum(values.values()) if complete else ''
            obs = metadata[key]
            evidence.append({'ticker': ticker, 'cik': spec['cik'], 'rule_id': spec['rule_id'], 'canonical_concept': spec['canonical_concept'], 'accession_number': key[0], 'form_type': obs.get('form', ''), 'fiscal_year_tag': obs.get('fy', ''), 'fiscal_period_tag': obs.get('fp', ''), 'period_start': key[1], 'period_end': key[2], 'component_values_json': json.dumps(values, separators=(',', ':'), sort_keys=True), 'component_count_required': len(spec['components']), 'component_count_present': len(values), 'missing_components': '|'.join(missing), 'canonical_value': total, 'unit': 'USD', 'continuity_status': 'COMPLETE' if complete else 'INCOMPLETE_COMPONENT_SET'})
        issuer_evidence = [row for row in evidence if row['ticker'] == ticker]
        complete_rows = [row for row in issuer_evidence if row['continuity_status'] == 'COMPLETE']
        summaries.append({'ticker': ticker, 'cik': spec['cik'], 'rule_id': spec['rule_id'], 'canonical_concept': spec['canonical_concept'], 'components': ' + '.join(spec['components']), 'eligible_accession_period_rows': len(issuer_evidence), 'complete_rows': len(complete_rows), 'incomplete_rows': len(issuer_evidence) - len(complete_rows), 'distinct_complete_periods': len(complete_periods), 'earliest_complete_period_end': min((end for _, end in complete_periods), default=''), 'latest_complete_period_end': max((end for _, end in complete_periods), default=''), 'mapping_status': 'APPROVED_V0_1' if complete_rows and len(complete_rows) == len(issuer_evidence) else 'REVIEW_REQUIRED'})
    with evidence_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(evidence[0]))
        writer.writeheader()
        writer.writerows(evidence)
    with summary_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    return (evidence, summaries)

def main() -> None:
    return None
if __name__ == '__main__':
    main()
