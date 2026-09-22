import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from mc.intelligence import research, competitors, strategy
except ImportError:
    research = competitors = strategy = None

NOW='2026-09-22T12:00:00Z'
TENANT='salem-botanicals'
OBJECTIVE='increase qualified leads'

def source(**overrides):
    return dict(dict(tenant_id=TENANT, source_id='source-1', source_uri='https://example.org/fixture',
        source_type='synthetic', observed_at='2026-09-21T12:00:00Z', confidence=0.8,
        relevance=0.9, applicability='Prospective customers seeking product information',
        finding='Product FAQs are an information gap', channel='website', format='FAQ',
        competitor='Synthetic competitor A', positioning='Educational', offers=[],
        reactions=[], limitations=['Fixture only; no real competitor observation']), **overrides)

class Intelligence(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(research), 'Research engine must exist')

    def test_mc005_preserves_evidence_and_computes_freshness(self):
        result=research(TENANT,OBJECTIVE,[source()],NOW)
        self.assertEqual(result[0]['age_days'],1)
        self.assertEqual(result[0]['provenance']['source_uri'],'https://example.org/fixture')
        self.assertEqual(result[0]['provenance']['freshness'],'fresh')
        self.assertEqual(result[0]['applicability'],'Prospective customers seeking product information')
        self.assertEqual(result, research(TENANT,OBJECTIVE,[source()],NOW))

    def test_mc005_rejects_bad_evidence_and_cross_tenant(self):
        for patch in [dict(tenant_id='other'),dict(confidence=2),dict(observed_at='2027-01-01T00:00:00Z'),
                      dict(source_uri='file:///secret'),dict(finding=''),dict(source_type='fabricated')]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                research(TENANT,OBJECTIVE,[source(**patch)],NOW)
        with self.assertRaises(ValueError):
            research(TENANT,OBJECTIVE,[source(),source()],NOW)

    def test_mc006_competitors_link_to_observed_evidence(self):
        evidence=research(TENANT,OBJECTIVE,[source()],NOW)
        result=competitors(TENANT,OBJECTIVE,evidence,NOW)
        self.assertEqual(result[0]['evidence_refs'],[evidence[0]['record_id']])
        self.assertEqual(result[0]['name'],'Synthetic competitor A')
        self.assertEqual(result[0]['offers'],[])

    def test_mc007_decision_changes_with_evidence_and_abstains_without_it(self):
        evidence=research(TENANT,OBJECTIVE,[source()],NOW)
        result=strategy(TENANT,OBJECTIVE,evidence,competitors(TENANT,OBJECTIVE,evidence,NOW),NOW)
        self.assertEqual(result['action'],'EXPERIMENT')
        self.assertEqual(result['channel'],'website')
        self.assertIn(evidence[0]['record_id'],result['evidence_refs'])
        changed=research(TENANT,OBJECTIVE,[source(channel='email',format='educational post')],NOW)
        self.assertEqual(strategy(TENANT,OBJECTIVE,changed,[],NOW)['channel'],'email')
        self.assertEqual(strategy(TENANT,OBJECTIVE,[],[],NOW)['action'],'HOLD')
        stale=research(TENANT,OBJECTIVE,[source(observed_at='2025-01-01T00:00:00Z')],NOW)
        self.assertEqual(strategy(TENANT,OBJECTIVE,stale,[],NOW)['action'],'HOLD')

    def test_mc007_cannot_consume_foreign_records(self):
        evidence=research(TENANT,OBJECTIVE,[source()],NOW)
        evidence[0]['tenant_id']='other'
        with self.assertRaises(ValueError):
            strategy(TENANT,OBJECTIVE,evidence,[],NOW)

if __name__=='__main__': unittest.main()
