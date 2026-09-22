import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from test_intelligence import source, NOW, TENANT, OBJECTIVE

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    from mc.workflow import run, review, delivery, normalize, attribute, learn
except ImportError:
    run=review=delivery=normalize=attribute=learn=None

def inputs():
    root=Path(__file__).resolve().parents[1]
    return dict(tenant=json.loads((root/'tenants/salem-botanicals.example.json').read_text()),
        objective=OBJECTIVE,sources=[source()],
        brand=dict(tenant_id=TENANT,name='Salem Botanicals',status='SYNTHETIC_SHADOW_PROFILE',
            approved_copy='Explore Salem Botanicals product information. Read our product FAQ and send us your questions.',
            cta='Read the FAQ',landing_url='https://example.org/salem-shadow',
            forbidden_terms=['guaranteed cure','treats cancer'],sensitive_targeting=False),
        analytics=dict(tenant_id=TENANT,source_type='synthetic',source_uri='https://example.org/analytics-fixture',
            observed_at=NOW,visits=100,leads=12,conversions=3,revenue=90,spend=0,
            attribution_evidence='none'),
        baseline=dict(tenant_id=TENANT,source_type='synthetic',visits=100,leads=5,window_days=7),
        window_days=7)

class Loop(unittest.TestCase):
    def setUp(self): self.assertTrue(callable(run),'Shadow workflow must exist')

    def test_mc008_to_016_persistent_end_to_end_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            result=run(inputs(),directory,NOW)
            self.assertEqual(result['state'],'SHADOW_COMPLETE')
            self.assertEqual(result['publication']['state'],'HANDOFF_READY')
            self.assertEqual(result['delivery']['state'],'NOT_PUBLISHED')
            self.assertEqual(result['attribution']['classification'],'UNKNOWN')
            self.assertIsNone(result['attribution']['attributed_revenue'])
            self.assertEqual(result['learning']['recommendation'],'EXPERIMENT')
            self.assertEqual(result['learning']['lead_rate_delta'],0.07)
            self.assertNotEqual(result['strategy']['record_id'],result['next_strategy']['record_id'])
            self.assertIn(result['learning']['record_id'],result['next_strategy']['evidence_refs'])
            self.assertTrue((Path(result['output_dir'])/'dashboard.html').is_file())
            self.assertTrue((Path(result['output_dir'])/'handoff.md').is_file())
            self.assertTrue((Path(result['output_dir'])/'manifest.json').is_file())
            again=run(inputs(),directory,NOW)
            self.assertEqual(again,result)

    def test_mc010_risky_or_unapproved_content_cannot_handoff(self):
        for patch in [dict(approved_copy='This guaranteed cure treats cancer'),dict(sensitive_targeting=True),dict(status='UNKNOWN')]:
            data=inputs(); data['brand'].update(patch)
            with tempfile.TemporaryDirectory() as directory:
                result=run(data,directory,NOW)
                self.assertEqual(result['state'],'REVIEW_BLOCKED')
                self.assertNotIn('publication',result)

    def test_no_production_mode_and_no_paid_spend(self):
        for patch in [dict(mode='production'),dict(analytics=dict(inputs()['analytics'],spend=1))]:
            data=inputs();data.update(patch)
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                run(data,directory,NOW)

    def test_mc012_acceptance_is_not_delivery_and_missing_tracking_fails(self):
        base=dict(tenant_id=TENANT,record_id='pub1',campaign_id='campaign1',content_id='content1')
        for receipt, expected in [(dict(accepted=True),'UNVERIFIED'),
            (dict(accepted=True,published=True,rendered=True,tracking=False),'TRACKING_FAILED'),
            (dict(accepted=True,published=True,rendered=True,tracking=True),'UNVERIFIED'),
            (dict(error='expired_auth'),'AUTH_EXPIRED'),(dict(error='rate_limit'),'RETRY_REQUIRED')]:
            with self.subTest(receipt=receipt):
                self.assertEqual(delivery(TENANT,OBJECTIVE,base,receipt,NOW)['state'],expected)

    def test_mc013_invalid_or_foreign_metrics_rejected(self):
        for patch in [dict(visits=-1),dict(leads=101),dict(revenue=float('nan')),dict(tenant_id='other')]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                normalize(TENANT,OBJECTIVE,dict(inputs()['analytics'],**patch),'c1',NOW)

    def test_mc014_classifications_never_invent_roi(self):
        for evidence,expected in [('none','UNKNOWN'),('temporal','CORRELATED'),('survey','LIKELY_INFLUENCED')]:
            metric=normalize(TENANT,OBJECTIVE,dict(inputs()['analytics'],attribution_evidence=evidence),'c1',NOW)
            result=attribute(TENANT,OBJECTIVE,metric,NOW)
            self.assertEqual(result['classification'],expected)
            self.assertIsNone(result['roas'])
        metric=normalize(TENANT,OBJECTIVE,dict(inputs()['analytics'],attribution_evidence='tracked',tracking_campaign_id='c1',
                verified_conversion_ids=['order1'],tracked_revenue=30),'c1',NOW)
        self.assertEqual(attribute(TENANT,OBJECTIVE,metric,NOW)['attributed_revenue'],30)
        metric['tracking_campaign_id']='wrong'
        self.assertEqual(attribute(TENANT,OBJECTIVE,metric,NOW)['classification'],'UNKNOWN')

    def test_mc015_outcomes_change_recommendation_and_insufficient_data_holds(self):
        for leads,expected in [(12,'EXPERIMENT'),(1,'REDUCE'),(5,'EXPERIMENT')]:
            data=inputs();data['analytics']['leads']=leads
            with tempfile.TemporaryDirectory() as directory:
                self.assertEqual(run(data,directory,NOW)['learning']['recommendation'],expected)
        data=inputs();data['analytics']['visits']=0;data['analytics']['leads']=0
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run(data,directory,NOW)['learning']['recommendation'],'HOLD')

    def test_tenant_isolation_at_each_input(self):
        for field in ['brand','analytics','baseline']:
            data=inputs();data[field]['tenant_id']='green-vine'
            with tempfile.TemporaryDirectory() as directory,self.assertRaises(ValueError):
                run(data,directory,NOW)

    def test_missing_analytics_is_visible_and_recoverable(self):
        data=inputs();data['analytics']=None
        with tempfile.TemporaryDirectory() as directory:
            result=run(data,directory,NOW)
            self.assertEqual(result['state'],'WAITING_ANALYTICS')
            self.assertEqual(result['status']['state'],'READY')
            self.assertEqual(run(inputs(),directory,NOW)['state'],'SHADOW_COMPLETE')

if __name__=='__main__': unittest.main()
