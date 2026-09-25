"""Real HTTP cooperative protocol qualification with injected response loss."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import hashlib
import shutil
import unittest
from unittest import mock
import test_command_center as fixtures
from test_intelligence import NOW

SUPERVISED_SOURCE=os.environ.get('MC_CC_SUPERVISED_SOURCE')
BETA_EVIDENCE=os.environ.get('MC_BETA_EVIDENCE')
SUPERVISED_SHA='9ab3dcd623b3a5b27738bed52b36a5285f2b4cb8'


@unittest.skipUnless(SUPERVISED_SOURCE,'Set MC_CC_SUPERVISED_SOURCE to isolated cooperative checkout')
class SupervisedTests(unittest.TestCase):
    setUp=fixtures.CommandCenterRoundtrip.setUp
    stop_server=fixtures.CommandCenterRoundtrip.stop_server
    queue_base=fixtures.CommandCenterRoundtrip.queue

    @classmethod
    def setUpClass(cls):
        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=SUPERVISED_SOURCE,text=True).strip()!=SUPERVISED_SHA:
            raise AssertionError('Cooperative reference revision mismatch')
        if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=SUPERVISED_SOURCE,text=True).strip():
            raise AssertionError('Cooperative reference has tracked modifications')
        spec=importlib.util.spec_from_file_location('supervised_cc',Path(SUPERVISED_SOURCE)/'server.py')
        cls.server=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.server)

    def queue(self):
        return self.queue_base(protocol='cooperative-v1')

    def execute(self):
        from mc.supervised import shadow_supervised
        return shadow_supervised(client=self.client,run_id='cc-r1',project_id='p1',
            provider_id='local',tenant_id=self.data['tenant']['tenant_id'],
            data=self.data,output_root=self.output,now=NOW)

    def preserve(self,name,result):
        if not BETA_EVIDENCE: return
        destination=Path(BETA_EVIDENCE)/name
        destination.mkdir(parents=True,exist_ok=False)
        shutil.copytree(self.server.DATA,destination/'command-center')
        shutil.copytree(self.output,destination/'marketing',ignore=shutil.ignore_patterns('writer.lock'))
        metadata=dict(state=result['state'],runtime=result.get('runtime'),
            production_published=False,cost_usd=0,
            command_center_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SUPERVISED_SOURCE,text=True).strip(),
            command_center_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in Path(SUPERVISED_SOURCE).glob('*.py')})
        (destination/'qualification.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        for path in destination.rglob('*'):
            if path.is_file():
                self.assertNotIn(self.worker_token.encode(),path.read_bytes())
                self.assertNotIn(self.owner_token.encode(),path.read_bytes())

    def test_supervised_entry_available(self):
        from mc import command_center
        self.assertTrue((Path(command_center.__file__).parent/'supervised.py').exists(),
                        'Cooperative worker required')

    def test_success_and_terminal_reconciliation_do_not_reexecute(self):
        self.queue()
        result=self.execute()
        self.assertEqual(result['state'],'SHADOW_COMPLETE')
        files={str(p):p.read_bytes() for p in self.output.rglob('*.json')}
        replay=self.execute()
        self.assertEqual(replay['run_id'],result['run_id'])
        self.assertEqual(files,{str(p):p.read_bytes() for p in self.output.rglob('*.json')})
        self.assertEqual(self.server.load_state()['runs'][0]['session_generation'],1)
        self.assertEqual(self.server.load_state()['workers'][0]['state'],'COMPLETE')
        self.preserve('success',result)

    def test_pause_between_stages_preserves_progress_then_resume_finishes(self):
        self.queue()
        from mc.modules import Registry
        original=Registry.call
        def pause_after(registry,*args,**kwargs):
            result=original(registry,*args,**kwargs)
            self.server.apply_control(dict(type='PAUSE_REQUESTED',project_id='p1'))
            return result
        with mock.patch.object(Registry,'call',pause_after):
            self.assertEqual(self.execute()['state'],'SUSPENDED')
        steps=list(self.output.rglob('step-*.json'))
        self.assertEqual(len(steps),1)
        before=steps[0].read_bytes()
        self.assertEqual(json.loads(before)['state'],'COMPLETE')
        self.assertEqual(self.execute()['state'],'SUSPENDED')
        self.server.apply_control(dict(type='RESUME_REQUESTED',project_id='p1'))
        result=self.execute()
        self.assertEqual(result['state'],'SHADOW_COMPLETE')
        self.assertEqual(steps[0].read_bytes(),before)
        self.preserve('pause-resume',result)

    def test_lost_acquire_response_and_expired_lease_resume(self):
        self.queue()
        original=self.client.request
        def lost(path,body=None):
            result=original(path,body)
            if path.endswith('/acquire'): raise ValueError('injected transport loss')
            return result
        with mock.patch.object(self.client,'request',lost):
            with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.server.load_state()['runs'][0]['status'],'RUNNING')
        with self.assertRaises(ValueError): self.execute()
        with mock.patch.object(self.server,'lease_clock',return_value=4102444800):
            self.assertEqual(self.execute()['state'],'SHADOW_COMPLETE')

    def test_lost_completion_response_reconciles_without_rerun(self):
        self.queue()
        original=self.client.request
        def lost(path,body=None):
            result=original(path,body)
            if path.endswith('/complete'): raise ValueError('injected transport loss')
            return result
        with mock.patch.object(self.client,'request',lost):
            with self.assertRaises(ValueError): self.execute()
        from mc import supervised
        with mock.patch.object(supervised,'run',side_effect=AssertionError('must not rerun')):
            self.assertEqual(self.execute()['state'],'SHADOW_COMPLETE')

    def test_worker_cannot_read_another_run_or_invoke_owner_control(self):
        self.queue()
        state=self.server.load_state()
        state['runs'][0]['worker_id']='other'
        self.server.save_state(state)
        for path,body in [('/api/execution/status?worker_id=w1&run_id=cc-r1',None),
                          ('/api/control',dict(type='RESUME_REQUESTED',project_id='p1'))]:
            with self.assertRaises(ValueError): self.client.request(path,body)

    def test_tampered_terminal_artifacts_are_rejected(self):
        self.queue()
        result=self.execute()
        (Path(result['output_dir'])/'handoff.md').write_text('tampered')
        with self.assertRaises(ValueError): self.execute()

    def test_cli_cooperative_execution_and_pause_exit(self):
        self.queue()
        command=fixtures.CommandCenterRoundtrip.worker_command(self)+['--supervised']
        env={**os.environ,'MC_CC_WORKER_TOKEN':self.worker_token}
        self.server.apply_control(dict(type='PAUSE_REQUESTED',project_id='p1'))
        paused=subprocess.run(command,cwd=Path(__file__).resolve().parents[1],env=env,
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(paused.returncode,3,paused.stderr)
        self.assertEqual(json.loads(paused.stdout)['state'],'SUSPENDED')
        self.server.apply_control(dict(type='RESUME_REQUESTED',project_id='p1'))
        done=subprocess.run(command,cwd=Path(__file__).resolve().parents[1],env=env,
                            capture_output=True,text=True,timeout=30)
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertEqual(json.loads(done.stdout)['state'],'SHADOW_COMPLETE')
        self.assertNotIn(self.worker_token,done.stdout+done.stderr)

    def test_failure_is_terminal_and_sanitized(self):
        self.data['objective']='private-unapproved'
        self.queue()
        with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.server.load_state()['runs'][0]['status'],'FAILED')
        self.assertEqual(self.server.load_state()['workers'][0]['state'],'FAILED')
        persisted='\n'.join(p.read_text() for p in self.server.DATA.rglob('*.json'))
        self.assertNotIn('private-unapproved',persisted)
        with self.assertRaises(ValueError): self.execute()

    def test_response_projection_does_not_leak_other_tenant_data(self):
        self.queue()
        state=self.server.load_state()
        state['projects'].append(dict(id='private',secret='other-tenant-secret'))
        self.server.save_state(state)
        responses=[]
        original=self.client.request
        def capture(path,body=None):
            value=original(path,body)
            responses.append(value)
            return value
        with mock.patch.object(self.client,'request',capture): self.execute()
        self.assertNotIn('other-tenant-secret',json.dumps(responses))

    def test_legacy_responses_cannot_leak_cooperative_sessions(self):
        self.queue_base()
        state=self.server.load_state()
        state['projects'].append(dict(id='private',secret='other-tenant-secret'))
        state['runs'].append(dict(id='private-run',worker_id='other',session_id='private-capability'))
        self.server.save_state(state)
        responses=[]
        original=self.client.request
        def capture(path,body=None):
            value=original(path,body)
            responses.append(value)
            return value
        with mock.patch.object(self.client,'request',capture):
            fixtures.CommandCenterRoundtrip.execute(self)
        self.assertNotIn('other-tenant-secret',json.dumps(responses))
        self.assertNotIn('private-capability',json.dumps(responses))

    def test_process_crash_releases_local_lock_and_replays_interrupted_stage(self):
        self.queue()
        command=fixtures.CommandCenterRoundtrip.worker_command(self)+['--supervised']
        driver=self.root/'crash.py'
        driver.write_text("import os,sys\nfrom mc.modules import Registry\n"
            "original=Registry.call\n"
            "def crash(self,*args,**kwargs):\n original(self,*args,**kwargs)\n os._exit(79)\n"
            "Registry.call=crash\nfrom mc.worker import main\nsys.exit(main())\n")
        crashed=subprocess.run([sys.executable,str(driver),*command[3:]],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]),
                 'MC_CC_WORKER_TOKEN':self.worker_token},capture_output=True,text=True,timeout=30)
        self.assertEqual(crashed.returncode,79,crashed.stderr)
        checkpoint=list(self.output.rglob('step-*.json'))
        self.assertEqual(len(checkpoint),1)
        self.assertEqual(json.loads(checkpoint[0].read_text())['state'],'RUNNING')
        with mock.patch.object(self.server,'lease_clock',return_value=4102444800):
            result=self.execute()
        self.assertEqual(result['state'],'SHADOW_COMPLETE')
        self.assertEqual(json.loads(checkpoint[0].read_text())['attempts'],2)
        self.assertFalse(result['production_published'])
        self.preserve('process-crash-recovery',result)

    def test_control_outage_stops_at_checkpoint_without_false_failure(self):
        self.queue()
        original=self.client.request
        calls=0
        def outage(path,body=None):
            nonlocal calls
            if path.endswith('/pulse'):
                calls+=1
                if calls==3: raise ValueError('injected network outage')
            return original(path,body)
        with mock.patch.object(self.client,'request',outage):
            with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.server.load_state()['runs'][0]['status'],'RUNNING')
        self.assertEqual(len(list(self.output.rglob('step-*.json'))),1)
        self.assertEqual(self.execute()['state'],'SHADOW_COMPLETE')

    def test_isolated_beta_launcher_creates_review_artifacts_without_credentials(self):
        process=subprocess.run([sys.executable,'-m','mc.beta','--command-center',SUPERVISED_SOURCE,
            '--output',str(self.root/'beta')],cwd=Path(__file__).resolve().parents[1],
            env=os.environ.copy(),capture_output=True,text=True,timeout=30)
        self.assertEqual(process.returncode,0,process.stderr+process.stdout)
        result=json.loads(process.stdout)
        self.assertEqual(result['state'],'SHADOW_COMPLETE')
        self.assertTrue(Path(result['dashboard']).is_file())
        self.assertFalse(result['production_published'])
        self.assertEqual(result['cost_usd'],0)
        self.assertNotIn(self.worker_token,process.stdout+process.stderr)
