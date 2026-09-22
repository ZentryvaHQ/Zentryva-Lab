import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from test_loop import inputs
from test_intelligence import NOW,TENANT,OBJECTIVE
from mc.workflow import run,normalize
from mc.core import runtime_provenance

class Hardening(unittest.TestCase):
    def test_manifest_cannot_drop_required_handoff_or_change_run_identity(self):
        for mutation in ('omit','identity'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                result=run(inputs(),directory,NOW)
                path=Path(result['output_dir'])/'manifest.json'
                manifest=json.loads(path.read_text())
                if mutation=='omit':del manifest['files']['handoff.md']
                else:manifest['run_id']='other-run'
                path.write_text(json.dumps(manifest),encoding='utf-8')
                with self.assertRaises(ValueError):run(inputs(),directory,NOW)

    def test_code_fingerprint_change_generates_new_run(self):
        with tempfile.TemporaryDirectory() as directory:
            before=run(inputs(),directory,NOW)
            provenance=runtime_provenance();provenance['source_sha256']='f'*64
            with patch('mc.workflow.runtime_provenance',return_value=provenance):
                after=run(inputs(),directory,NOW)
            self.assertNotEqual(before['run_id'],after['run_id'])

    def test_non_synthetic_metrics_require_explicit_campaign_binding(self):
        raw=dict(inputs()['analytics'],source_type='authorized_client_data')
        with self.assertRaises(ValueError):normalize(TENANT,OBJECTIVE,raw,'c1',NOW)

    def test_review_covers_cta_and_creative_fields(self):
        data=inputs();data['brand']['cta']='Buy this guaranteed cure that treats cancer'
        with tempfile.TemporaryDirectory() as directory:
            result=run(data,directory,NOW)
            self.assertEqual(result['state'],'REVIEW_BLOCKED')

    def test_metrics_and_baseline_cannot_be_rebound(self):
        for patch in [dict(campaign_id='other-campaign'),dict(objective='unrelated-objective')]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                normalize(TENANT,OBJECTIVE,dict(inputs()['analytics'],**patch),'c1',NOW)
        data=inputs();data['baseline']['objective']='unrelated-objective'
        with tempfile.TemporaryDirectory() as directory,self.assertRaises(ValueError):
            run(data,directory,NOW)

    def test_impossible_conversions_and_overcredited_orders_rejected(self):
        for changes in [dict(conversions=101),dict(conversions=0,verified_conversion_ids=['order1']),dict(conversions=1,verified_conversion_ids=['a','b'])]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                normalize(TENANT,OBJECTIVE,dict(inputs()['analytics'],**changes),'c1',NOW)

    def test_replay_after_copy_uses_current_location(self):
        with tempfile.TemporaryDirectory() as first,tempfile.TemporaryDirectory() as second:
            original=run(inputs(),first,NOW)
            shutil.copytree(Path(first)/TENANT,Path(second)/TENANT)
            copied=run(inputs(),second,NOW)
            self.assertEqual(Path(copied['output_dir']).parent.parent,Path(second))

    def test_manifest_records_runtime_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            result=run(inputs(),directory,NOW)
            manifest=json.loads((Path(result['output_dir'])/'manifest.json').read_text())
            self.assertIn('runtime',manifest)
            self.assertEqual(len(manifest['runtime']['source_sha256']),64)
            self.assertIn('git_commit',manifest['runtime'])

if __name__=='__main__':unittest.main()
