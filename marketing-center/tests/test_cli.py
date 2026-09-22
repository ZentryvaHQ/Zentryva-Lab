import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_loop import inputs
from test_intelligence import NOW
from mc.workflow import run

ROOT=Path(__file__).resolve().parents[1]

class Operator(unittest.TestCase):
    def test_cli_writes_report_and_handles_invalid_input_without_payload_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'inputs.json';path.write_text(json.dumps(inputs()),encoding='utf-8')
            process=subprocess.run([sys.executable,'-m','mc','--input',str(path),'--output',directory,'--at',NOW],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertIn('SHADOW_COMPLETE',process.stdout)
            path.write_text('{bad syntax private-example-value',encoding='utf-8')
            bad=subprocess.run([sys.executable,'-m','mc','--input',str(path),'--output',directory],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(bad.returncode,2)
            self.assertNotIn('private-example-value',bad.stderr)

    def test_replay_checks_evidence_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            result=run(inputs(),directory,NOW)
            (Path(result['output_dir'])/'handoff.md').write_text('modified',encoding='utf-8')
            with self.assertRaises(ValueError): run(inputs(),directory,NOW)

    def test_traceability_graph_and_tenant_portability(self):
        with tempfile.TemporaryDirectory() as directory:
            salem=run(inputs(),directory,NOW)
            data=inputs();data['tenant']['tenant_id']='other-pilot'
            for field in ('brand','analytics','baseline'):data[field]['tenant_id']='other-pilot'
            for row in data['sources']:row['tenant_id']='other-pilot'
            other=run(data,directory,NOW)
            self.assertNotEqual(salem['output_dir'],other['output_dir'])
            rows=[json.loads(x) for x in (Path(other['output_dir'])/'records.jsonl').read_text().splitlines()]
            ids={r['record_id'] for r in rows}
            self.assertEqual(len(ids),len(rows))
            for row in rows:
                self.assertEqual(row['tenant_id'],'other-pilot')
                self.assertTrue(set(row['evidence_refs'])<=ids)

    def test_untrusted_text_is_escaped_in_dashboard(self):
        data=inputs();data['sources'][0]['finding']='<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as directory:
            result=run(data,directory,NOW)
            page=(Path(result['output_dir'])/'dashboard.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>',page)
            self.assertIn('&lt;script&gt;',page)

if __name__=='__main__':unittest.main()
