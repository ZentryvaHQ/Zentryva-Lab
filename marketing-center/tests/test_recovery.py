import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_loop import inputs
from test_intelligence import NOW
from mc.workflow import run
try:
    from mc.recovery import Journal
except ImportError:
    Journal=None

class Recovery(unittest.TestCase):
    def setUp(self):self.assertTrue(callable(Journal),'Durable shadow step adapter required')

    def test_completed_step_survives_process_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            script="from mc.recovery import Journal; import os; j=Journal("+repr(directory)+"); j.__enter__(); j.call('sample',lambda: {'value':7}); os._exit(9)"
            child=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(child.returncode,9)
            with Journal(directory) as journal:
                self.assertEqual(journal.call('sample',lambda: self.fail('completed step reran')),{'value':7})

    def test_second_writer_is_rejected_and_retry_after_release_works(self):
        with tempfile.TemporaryDirectory() as directory:
            with Journal(directory):
                with self.assertRaises(ValueError):
                    with Journal(directory):pass
            with Journal(directory) as journal:self.assertEqual(journal.call('x',lambda:3),3)

    def test_failure_is_sanitized_and_manual_restart_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            with Journal(directory) as journal:
                with self.assertRaises(ValueError):journal.call('bad',lambda: (_ for _ in ()).throw(RuntimeError('private-value')))
            self.assertNotIn('private-value',''.join(p.read_text() for p in Path(directory).glob('*.json')))
            with Journal(directory) as journal:self.assertEqual(journal.call('bad',lambda:4),4)

    def test_tampered_step_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            with Journal(directory) as journal:journal.call('x',lambda:3)
            path=next(Path(directory).glob('step-*.json'))
            item=json.loads(path.read_text());item['result']=9;path.write_text(json.dumps(item))
            with Journal(directory) as journal,self.assertRaises(ValueError):journal.call('x',lambda:3)

    def test_interrupted_workflow_resumes_verified_steps(self):
        from mc import stages,intelligence
        with tempfile.TemporaryDirectory() as directory:
            with patch('mc.stages.create_content',side_effect=RuntimeError('interrupted')):
                with self.assertRaises(ValueError):run(inputs(),directory,NOW)
            with patch('mc.intelligence.research',side_effect=AssertionError('research must be reused')):
                self.assertEqual(run(inputs(),directory,NOW)['state'],'SHADOW_COMPLETE')

if __name__=='__main__':unittest.main()
