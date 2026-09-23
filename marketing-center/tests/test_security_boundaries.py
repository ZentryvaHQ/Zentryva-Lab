from pathlib import Path
import tempfile
import unittest
from test_loop import inputs
from test_intelligence import NOW,TENANT,OBJECTIVE
from mc.workflow import run,delivery
from mc.recovery import Journal

class SecurityBoundaries(unittest.TestCase):
    def test_receipt_requires_matching_all_identities(self):
        publication=dict(tenant_id=TENANT,record_id='pub',campaign_id='campaign',content_id='content')
        valid=dict(tenant_id=TENANT,campaign_id='campaign',content_id='content',error='expired_auth')
        self.assertEqual(delivery(TENANT,OBJECTIVE,publication,valid,NOW)['state'],'AUTH_EXPIRED')
        for key in ('tenant_id','campaign_id','content_id'):
            for value in ('foreign',None):
                receipt=dict(valid);receipt[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):delivery(TENANT,OBJECTIVE,publication,receipt,NOW)

    def test_credentials_are_rejected_before_persistence(self):
        for place in ('brand','analytics'):
            data=inputs();data[place]['api_key']='fixture-private-value'
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):run(data,directory,NOW)
                self.assertEqual(list(Path(directory).iterdir()),[])

    def test_sensitive_url_parameters_rejected(self):
        data=inputs();data['brand']['landing_url']='https://example.org/path?access_token=fixture-value'
        with tempfile.TemporaryDirectory() as directory,self.assertRaises(ValueError):run(data,directory,NOW)

    def test_normalized_urls_and_oauth_fragments_cannot_bypass_filter(self):
        for url in ('HTTPS://example.org/path?access_token=fixture-value',
                    ' https://example.org/path?access_token=fixture-value',
                    'https://example.org/path#access_token=fixture-value'):
            data=inputs();data['brand']['landing_url']=url
            with self.subTest(url=url),tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):run(data,directory,NOW)
                self.assertEqual(list(Path(directory).iterdir()),[])

    def test_retry_budget_and_deadline_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            for _ in range(3):
                with Journal(directory) as journal,self.assertRaises(ValueError):journal.call('x',lambda:1/0)
            with Journal(directory) as journal,self.assertRaisesRegex(ValueError,'budget'):journal.call('x',lambda:7)
        with tempfile.TemporaryDirectory() as directory,Journal(directory,deadline_seconds=0) as journal:
            with self.assertRaisesRegex(ValueError,'deadline'):journal.call('x',lambda:7)

if __name__=='__main__':unittest.main()
