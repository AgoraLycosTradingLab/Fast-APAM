import csv
import json
import tempfile
import unittest
from pathlib import Path

from fast_apam.canonical_preparation import select_facts
from fast_apam.signal_preparation import construct_signals


def write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class CanonicalPreparationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.acc = '0000000001-26-000001'
        self.target = {'batch_id': 'CUSTOMER_DISCOVERY', 'model_date': '2026-07-31',
                       'ticker': 'TEST', 'cik': '0000000001', 'accession_number': self.acc,
                       'model_available_date': '2026-07-30', 'source_url': 'https://www.sec.gov/test',
                       'form_type': '10-Q', 'report_period': '2026-06-30',
                       'accepted_timestamp_utc': '2026-07-29T20:00:00+00:00',
                       'primary_document': 'report.htm'}
        self.candidate = {'batch_id': 'CUSTOMER_DISCOVERY', 'model_date': '2026-07-31',
                          'ticker': 'TEST', 'cik': '0000000001', 'accession_number': self.acc,
                          'model_available_date': '2026-07-30', 'canonical_concept': 'revenue',
                          'taxonomy_concept': 'Revenues', 'mapping_priority': '3',
                          'value': '120', 'unit': 'USD', 'period_start': '2026-04-01',
                          'period_end': '2026-06-30', 'companyfacts_payload_sha256': 'cfhash'}
        self.inline = {'model_date': '2026-07-31', 'ticker': 'TEST', 'cik': '0000000001',
                       'accession_number': self.acc, 'model_available_date': '2026-07-30',
                       'taxonomy_concept': 'us-gaap:Revenues', 'parsed_value': '120',
                       'period_start': '2026-04-01', 'period_end': '2026-06-30',
                       'fact_type': 'NUMERIC', 'dimension_count': '0',
                       'consolidation_scope': 'CONSOLIDATED_DEFAULT', 'period_type': 'DURATION',
                       'entity_identifier': '1', 'unit_ref': 'USD', 'context_id': 'c1',
                       'fact_id': 'f1', 'decimals': '-3', 'filing_payload_sha256': 'htmlhash'}
        self.audit = {'accession_number': self.acc, 'status': 'EXTRACTED_CANDIDATE_CONTEXTS',
                      'filing_payload_sha256': 'htmlhash'}
        (self.folder / 'preparation.json').write_text(json.dumps({'model_date': '2026-07-31'}))
        (self.folder / 'inline_context_summary.json').write_text(json.dumps(
            {'model_date': '2026-07-31', 'ready_to_score': False}))

    def save(self, candidates=None, inline=None):
        write(self.folder / 'filing_targets.csv', [self.target])
        write(self.folder / 'inline_context_audit.csv', [self.audit])
        write(self.folder / 'candidate_facts.csv', candidates or [self.candidate])
        write(self.folder / 'inline_facts.csv', inline or [self.inline])

    def test_exact_context_produces_audited_candidate_parent(self):
        self.save()
        result = select_facts(self.folder)
        self.assertEqual(result['canonical_fact_count'], 1)
        self.assertFalse(result['ready_to_score'])
        with (self.folder / 'canonical_facts.csv').open(newline='') as handle:
            row = list(csv.DictReader(handle))[0]
        self.assertEqual(row['duration_class'], 'QUARTER')
        self.assertEqual(row['rounding_error_bound'], '500')
        self.assertEqual(row['filing_payload_sha256'], 'htmlhash')

    def test_nonpositive_value_is_preserved_for_later_fallback(self):
        self.candidate['value'] = self.inline['parsed_value'] = '-25'
        self.save()
        self.assertEqual(select_facts(self.folder)['canonical_fact_count'], 1)
        self.assertIn('-25', (self.folder / 'canonical_facts.csv').read_text())

    def test_dimensioned_or_missing_context_is_held(self):
        self.inline['dimension_count'] = '1'
        self.inline['consolidation_scope'] = 'DIMENSIONED'
        self.save()
        result = select_facts(self.folder)
        self.assertEqual(result['canonical_fact_count'], 0)
        self.assertIn('REVIEW_NO_EXACT_CONTEXT', (self.folder / 'canonical_fact_audit.csv').read_text())

    def test_multiple_default_contexts_are_held(self):
        other = dict(self.inline, context_id='c2', fact_id='f2')
        self.save(inline=[self.inline, other])
        result = select_facts(self.folder)
        self.assertEqual(result['canonical_fact_count'], 0)
        self.assertIn('REVIEW_MULTIPLE_CONTEXTS', (self.folder / 'canonical_fact_audit.csv').read_text())

    def test_future_candidate_is_rejected(self):
        self.target['model_available_date'] = self.candidate['model_available_date'] = '2026-08-03'
        self.inline['model_available_date'] = '2026-08-03'
        self.save()
        with self.assertRaisesRegex(ValueError, 'cutoff'):
            select_facts(self.folder)

    def test_incomparable_period_is_held(self):
        self.candidate['period_start'] = self.inline['period_start'] = '2026-06-01'
        self.save()
        result = select_facts(self.folder)
        self.assertEqual(result['canonical_fact_count'], 0)
        self.assertIn('REVIEW_INCOMPARABLE_PERIOD', (self.folder / 'canonical_fact_audit.csv').read_text())

    def test_existing_quarter_constructor_reconciles_direct_and_ytd(self):
        q1 = dict(self.candidate, value='110', period_start='2026-01-01',
                  period_end='2026-03-31')
        half = dict(self.candidate, value='230', period_start='2026-01-01')
        q1_inline = dict(self.inline, parsed_value='110', period_start='2026-01-01',
                         period_end='2026-03-31', context_id='q1', fact_id='q1f')
        half_inline = dict(self.inline, parsed_value='230', period_start='2026-01-01',
                           context_id='h1', fact_id='h1f')
        self.save(candidates=[q1, half, self.candidate],
                  inline=[q1_inline, half_inline, self.inline])
        self.assertEqual(select_facts(self.folder)['canonical_fact_count'], 3)
        result = construct_signals(self.folder)
        self.assertEqual(result['quarter_count'], 2)
        self.assertEqual(result['ttm_yoy_observation_count'], 0)
        with (self.folder / 'standalone_quarters.csv').open(newline='') as handle:
            quarters = list(csv.DictReader(handle))
        self.assertEqual(quarters[-1]['standalone_value'], '120')
        self.assertEqual(quarters[-1]['quarter_status'], 'PASS_DIRECT_DERIVED_RECONCILED')
        self.assertFalse(result['ready_to_score'])


if __name__ == '__main__':
    unittest.main()
