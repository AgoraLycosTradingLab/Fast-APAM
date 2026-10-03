import json
import os
import tempfile
import unittest
import zlib
import zipfile
from pathlib import Path
from unittest.mock import patch
from fast_apam.storage import Store,sha
from fast_apam.snapshots import safe_name,rows
from fast_apam.runner import csv_bytes,verify_outputs,publish,export_audit
from fast_apam.acquisition import fetch_new,validate_url


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.store=Store(self.root/'model.sqlite')
        self.addCleanup(self.store.close)
        self.files={('input','a.csv'):b'ticker,value\nTEST,3\n'}
        self.config={'model_date':'2026-09-25'}

    def test_immutable_idempotent_import(self):
        a=self.store.import_snapshot('2026-09-25',self.config,self.files)
        self.assertEqual(a,self.store.import_snapshot('2026-09-25',self.config,self.files))
        self.assertEqual(self.store.files('2026-09-25'),{'a.csv':self.files['input','a.csv']})
        with self.assertRaises(ValueError):self.store.import_snapshot('2026-09-25',self.config,{('input','a.csv'):b'changed'})

    def test_blob_deduplication(self):
        with self.store.db:
            self.assertEqual(self.store.put(b'same'),self.store.put(b'same'))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM blobs').fetchone()[0],1)

    def test_corrupt_blob_detected(self):
        with self.store.db:
            digest=self.store.put(b'original')
            self.store.db.execute('UPDATE blobs SET payload=? WHERE hash=?',(zlib.compress(b'wrong'),digest))
        with self.assertRaises(ValueError):self.store.get(digest)

    def test_cross_date_isolation(self):
        self.store.import_snapshot('2026-09-25',self.config,self.files)
        self.store.import_snapshot('2026-07-31',{'model_date':'2026-07-31'},{('input','a.csv'):b'old'})
        self.assertNotEqual(self.store.files('2026-07-31'),self.store.files('2026-09-25'))

    def test_config_tampering_detected(self):
        self.store.import_snapshot('2026-09-25',self.config,self.files)
        with self.store.db:self.store.db.execute('UPDATE snapshots SET config=?', ('{"model_date":"2026-07-31"}',))
        with self.assertRaises(ValueError):self.store.snapshot('2026-09-25')

    def test_existing_output_not_overwritten(self):
        target=self.root/'output';target.mkdir();(target/'results.csv').write_text('preserve')
        with self.assertRaises(ValueError):publish(self.store,'2026-09-25',target)
        self.assertEqual((target/'results.csv').read_text(),'preserve')

    def test_path_traversal(self):
        for name in ['../secret','C:/secret','/secret','..\\secret']:
            with self.assertRaises(ValueError):safe_name(name)

    def test_reference_difference_detected(self):
        self.store.import_snapshot('2026-09-25',self.config,{('reference','result.csv'):b'ticker,score\nTEST,1\n'})
        self.assertFalse(verify_outputs(self.store,'2026-09-25',{'result.csv':b'ticker,score\nTEST,2\n'})['passed'])

    def test_no_reference_does_not_pass(self):
        with self.assertRaises(ValueError):verify_outputs(self.store,'2026-09-25',{})

    def test_empty_exceptions_preserve_headers(self):
        self.assertEqual(csv_bytes([],['ticker','reason']),b'ticker,reason\r\n')

    def test_audit_export_requires_successful_run(self):
        with self.assertRaises(ValueError):export_audit(self.store,'absent',self.root/'audit.zip')

    def test_audit_export_keeps_exact_input_and_output_bytes(self):
        self.store.import_snapshot('2026-09-25',self.config,self.files)
        self.store.save_run('test-run','2026-09-25',{'status':'COMPLETE'},{'results.csv':b'ticker,score\nTEST,5\n'})
        path=self.root/'audit.zip'
        export_audit(self.store,'test-run',path)
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read('a.csv'),self.files['input','a.csv'])
            self.assertEqual(archive.read('results.csv'),b'ticker,score\nTEST,5\n')
        with self.assertRaises(FileExistsError):export_audit(self.store,'test-run',path)


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'db');self.addCleanup(self.store.close)
        self.row={'model_date':'2026-09-25','eligible_on_model_date':'Y','model_available_date':'2026-09-24','accession_number':'test-001','source_url':'https://www.sec.gov/Archives/edgar/data/1/001/doc.htm'}

    def test_identical_filing_not_downloaded_twice(self):
        calls=[]
        def transport(url,agent):calls.append(url);return b'<html>fact</html>'
        with patch.dict(os.environ,{'APAM_SEC_USER_AGENT':'test contact@example.com'}):
            first=fetch_new(self.store,csv_bytes([self.row]),'2026-09-25',transport,0)
            second=fetch_new(self.store,csv_bytes([self.row]),'2026-09-25',transport,0)
        self.assertEqual((first['downloaded'],second['cache_hits'],len(calls)),(1,1,1))

    def test_amendment_is_a_distinct_document(self):
        amendment=dict(self.row,accession_number='test-002',source_url='https://www.sec.gov/Archives/edgar/data/1/002/amendment.htm')
        with patch.dict(os.environ,{'APAM_SEC_USER_AGENT':'test contact@example.com'}):
            result=fetch_new(self.store,csv_bytes([self.row,amendment]),'2026-09-25',lambda u,a:b'data',0)
        self.assertEqual(result['downloaded'],2)

    def test_identity_requested_once_and_not_for_cached_documents(self):
        other=dict(self.row,accession_number='test-002',source_url='https://www.sec.gov/Archives/edgar/data/1/002/doc.htm')
        index=csv_bytes([self.row,other])
        with patch('fast_apam.acquisition.sec_user_agent', return_value='Private contact@example.com') as identity:
            result=fetch_new(self.store,index,'2026-09-25',lambda u,a:b'facts',0)
            identity.assert_called_once_with()
        with patch('fast_apam.acquisition.sec_user_agent', side_effect=AssertionError('Cached run must not prompt')):
            cached=fetch_new(self.store,index,'2026-09-25',delay=0)
        self.assertEqual((result['downloaded'],cached['cache_hits']),(2,2))
        self.assertNotIn('Private contact@example.com',str(result))
        self.assertNotIn('Private contact@example.com','\n'.join(self.store.db.iterdump()))

    def test_future_eligible_filing_rejected(self):
        with self.assertRaises(ValueError):fetch_new(self.store,csv_bytes([dict(self.row,model_available_date='2026-09-28')]),'2026-09-25',delay=0)

    def test_ineligible_filing_not_downloaded(self):
        result=fetch_new(self.store,csv_bytes([dict(self.row,eligible_on_model_date='N')]),'2026-09-25',delay=0)
        self.assertEqual(result['downloaded'],0)

    def test_failed_download_is_resumable(self):
        def failure(u,a):raise TimeoutError()
        with patch.dict(os.environ,{'APAM_SEC_USER_AGENT':'test contact@example.com'}):
            first=fetch_new(self.store,csv_bytes([self.row]),'2026-09-25',failure,0)
            second=fetch_new(self.store,csv_bytes([self.row]),'2026-09-25',lambda u,a:b'ok',0)
        self.assertEqual(first['status'],'INCOMPLETE')
        self.assertEqual(second['downloaded'],1)

    def test_untrusted_url_rejected(self):
        for url in ['http://www.sec.gov/Archives/edgar/data/1/x','https://example.com/x','https://www.sec.gov.evil.test/Archives/edgar/data/1/x']:
            with self.assertRaises(ValueError):validate_url(url)
