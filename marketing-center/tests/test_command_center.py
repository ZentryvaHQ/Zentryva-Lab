"""Real local HTTP qualification against a pinned Command Center checkout."""
import copy
import hashlib
import http.client
from http.server import ThreadingHTTPServer
import importlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from test_loop import inputs
from test_intelligence import NOW, TENANT

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from mc.command_center import LocalCommandCenter, shadow_once, request_binding
except ImportError:
    LocalCommandCenter = shadow_once = request_binding = None

CC_SHA = 'fc8e82b51693f938173bc1ce7ca7314a64e2fb74'
CC_SOURCE = os.environ.get('MC_CC_SOURCE')


class AdapterBoundary(unittest.TestCase):
    def test_transport_is_local_only(self):
        self.assertTrue(callable(LocalCommandCenter), 'Local Command Center adapter required')
        for url in ['https://example.org', 'http://localhost:80', 'http://127.0.0.1:80/path',
                    'http://user@127.0.0.1:80', 'http://127.0.0.1:80?x=1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                LocalCommandCenter(url, 'w1', 'fixture-only')


@unittest.skipUnless(CC_SOURCE, 'Set MC_CC_SOURCE to pinned isolated Command Center checkout')
class CommandCenterRoundtrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CC_SOURCE, text=True).strip()
        if actual != CC_SHA:
            raise AssertionError('Command Center revision differs from qualified interface')
        if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                                   cwd=CC_SOURCE, text=True).strip():
            raise AssertionError('Command Center tracked reference files are modified')
        sys.path.insert(0, CC_SOURCE)
        cls.server = importlib.import_module('server')
        if Path(cls.server.__file__).resolve() != (Path(CC_SOURCE)/'server.py').resolve():
            raise AssertionError('Loaded Command Center module is outside pinned reference')

    def setUp(self):
        self.assertTrue(callable(shadow_once), 'Shadow adapter required')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / 'marketing'
        self.server.DATA = self.root / 'cc'
        self.server.DATA.mkdir()
        self.server.STATE = self.server.DATA / 'state.json'
        self.server.EVENTS = self.server.DATA / 'events.jsonl'
        self.server.EVENTS.touch()
        self.server.STATE.write_text(json.dumps(dict(settings={'stall_after_seconds':900},
            projects=[dict(id='p1', status='RUNNING', desired_state='RUNNING', assigned_worker_id='w1')],
            workers=[dict(id='w1', state='IDLE', current_project_id='p1')],
            providers=[dict(id='local', enabled=True)], attention=[], runs=[])), encoding='utf-8')
        self.owner_token, self.worker_token = secrets.token_hex(32), secrets.token_hex(32)
        self.evidence_output = os.environ.get('MC_CC_EVIDENCE')
        # Windows subprocess sockets require SystemRoot; preserve only OS runtime
        # settings, never ambient provider/production credentials in this fixture.
        runtime_env = {key:value for key,value in os.environ.items()
                       if key.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP'}}
        patcher = mock.patch.dict(os.environ, {**runtime_env, 'ZENTRYVA_CONTROL_TOKEN':self.owner_token,
            'ZENTRYVA_WORKER_TOKENS':json.dumps({'w1':self.worker_token})}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        class QuietHandler(self.server.Handler):
            def log_message(self, *args): pass
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.client = LocalCommandCenter(f'http://127.0.0.1:{self.http.server_port}', 'w1', self.worker_token)
        self.data = inputs()

    def stop_server(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()

    def queue(self, **changes):
        payload = dict(run_id='cc-r1', project_id='p1', provider_id='local', worker_id='w1',
            action='marketing.shadow.verify', input=request_binding(self.data, NOW))
        payload.update(changes)
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=5)
        conn.request('POST', '/api/execution/request', json.dumps(payload),
            {'Authorization':'Bearer '+self.owner_token, 'Content-Type':'application/json'})
        response = conn.getresponse()
        status, result = response.status, json.loads(response.read())
        conn.close()
        self.assertEqual(status, 201)
        return result

    def execute(self, **changes):
        args = dict(client=self.client, run_id='cc-r1', project_id='p1', provider_id='local',
                    tenant_id=TENANT, data=self.data, output_root=self.output, now=NOW)
        args.update(changes)
        return shadow_once(**args)

    def test_real_authenticated_shadow_roundtrip(self):
        self.queue()
        result = self.execute()
        self.assertEqual(result['state'], 'SHADOW_COMPLETE')
        marketing_head = subprocess.check_output(['git','rev-parse','HEAD'],
            cwd=Path(__file__).resolve().parents[1], text=True).strip()
        self.assertEqual(result['runtime']['git_commit'], marketing_head)
        state = self.server.load_state()
        remote = state['runs'][0]
        self.assertEqual(remote['status'], 'COMPLETE')
        self.assertFalse(result['production_published'])
        self.assertEqual(result['cost_usd'], 0)
        self.assertEqual(state['workers'][0]['state'], 'COMPLETE')
        for kind, key in [('receipt','receipt_ref'), ('checkpoint','checkpoint_ref'), ('result','evidence_ref')]:
            self.server.require_evidence(remote[key], kind, 'cc-r1', 'w1')
        persisted = '\n'.join(p.read_text(encoding='utf-8') for p in self.root.rglob('*.json'))
        self.assertNotIn(self.worker_token, persisted)
        self.assertNotIn(self.owner_token, persisted)
        with self.assertRaises(ValueError):
            self.execute()
        if self.evidence_output:
            destination = Path(self.evidence_output)
            destination.mkdir(parents=True, exist_ok=False)
            shutil.copytree(self.server.DATA, destination/'command-center')
            shutil.copytree(self.output, destination/'marketing')
            (destination/'qualification.json').write_text(json.dumps(dict(
                command_center_sha=CC_SHA, marketing_runtime=result['runtime'],
                command_center_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in Path(CC_SOURCE).glob('*.py')},
                state=result['state'], production_published=False, cost_usd=0,
                transport='real HTTP on ephemeral 127.0.0.1 port',
                provider_supervision='UNVERIFIED', remote_run=remote), indent=2), encoding='utf-8')

    def test_wrong_action_and_payload_are_rejected_before_ack_or_output(self):
        for changes in [dict(action='publish'), dict(input={'tenant_id':'other'}),
                        dict(requires_owner_approval=True)]:
            with self.subTest(changes=changes):
                state = self.server.load_state(); state['runs'] = []; self.server.save_state(state)
                self.queue(**changes)
                with self.assertRaises(ValueError): self.execute()
                self.assertFalse(self.output.exists())
                self.assertNotEqual(self.server.load_state()['runs'][0]['status'], 'RUNNING')

    def test_wrong_tenant_and_credentials_rejected_before_transport(self):
        for changes in [dict(tenant_id='other'), dict(data={**self.data, 'api_key':'fixture'})]:
            with self.subTest(changes=changes), mock.patch.object(self.client, 'request') as call:
                with self.assertRaises(ValueError): self.execute(**changes)
                call.assert_not_called()

    def test_bad_auth_is_sanitized(self):
        self.queue()
        client = LocalCommandCenter(f'http://127.0.0.1:{self.http.server_port}', 'w1', 'wrong-secret')
        with self.assertRaisesRegex(ValueError, '^Command Center request failed$'):
            self.execute(client=client)
        self.assertFalse(self.output.exists())

    def test_incomplete_shadow_is_failed_not_complete(self):
        self.data['sources'] = []
        self.queue()
        result = self.execute()
        self.assertEqual(result['state'], 'EVIDENCE_HOLD')
        self.assertEqual(self.server.load_state()['runs'][0]['status'], 'FAILED')

    def test_paused_project_does_not_execute_local_work(self):
        self.queue()
        state = self.server.load_state()
        state['projects'][0]['desired_state'] = 'PAUSED'
        self.server.save_state(state)
        with self.assertRaisesRegex(ValueError, 'Local shadow failed'):
            self.execute()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.server.load_state()['runs'][0]['status'], 'FAILED')

    def test_pause_arriving_during_shadow_stops_safely(self):
        self.queue()
        def pause_then_probe(data, output_root, now, control=None):
            state=self.server.load_state()
            state['projects'][0]['desired_state']='PAUSED'
            self.server.save_state(state)
            control()
        with mock.patch('mc.command_center.run', side_effect=pause_then_probe):
            with self.assertRaisesRegex(ValueError,'stopped by shared control'):
                self.execute()
        state=self.server.load_state()
        self.assertEqual(state['runs'][0]['status'],'FAILED')
        self.assertEqual(state['workers'][0]['state'],'WAITING_FOR_DEPENDENCY')
        self.assertFalse(self.output.exists())

    def test_local_validation_failure_is_reported_without_exception_content(self):
        self.data['objective'] = 'unapproved-objective'
        self.queue()
        with self.assertRaisesRegex(ValueError, '^Local shadow failed; evidence preserved$'):
            self.execute()
        state = self.server.load_state()
        self.assertEqual(state['runs'][0]['status'], 'FAILED')
        self.assertEqual(state['workers'][0]['state'], 'FAILED')
        persisted = '\n'.join(p.read_text(encoding='utf-8') for p in self.server.DATA.rglob('*.json'))
        self.assertNotIn('unapproved-objective', persisted)

    def test_lost_completion_response_does_not_repeat_shadow_work(self):
        self.queue()
        original = self.client.request
        def lose_reply(path, body=None):
            result = original(path, body)
            if path == '/api/execution/complete':
                raise ValueError('Command Center request failed')
            return result
        with mock.patch.object(self.client, 'request', side_effect=lose_reply):
            with self.assertRaisesRegex(ValueError, 'Command Center request failed'):
                self.execute()
        self.assertEqual(self.server.load_state()['runs'][0]['status'], 'COMPLETE')
        self.assertEqual(len(list(self.output.glob('*/run-*/result.json'))), 1)
        with self.assertRaises(ValueError): self.execute()
        self.assertEqual(len(list(self.output.glob('*/run-*/result.json'))), 1)

    def worker_command(self):
        input_path = self.root/'input.json'
        input_path.write_text(json.dumps(self.data), encoding='utf-8')
        return [sys.executable, '-m', 'mc.worker', '--url', f'http://127.0.0.1:{self.http.server_port}',
                '--worker-id', 'w1', '--run-id', 'cc-r1', '--project-id', 'p1', '--provider-id', 'local',
                '--tenant-id', TENANT, '--input', str(input_path), '--output', str(self.output), '--at', NOW]

    def test_operator_cli_runs_real_queued_shadow(self):
        self.queue()
        process = subprocess.run(self.worker_command(), cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, 'MC_CC_WORKER_TOKEN':self.worker_token}, capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        output = json.loads(process.stdout)
        self.assertEqual(output['state'], 'SHADOW_COMPLETE')
        self.assertFalse(output['production_published'])
        self.assertNotIn(self.worker_token, process.stdout+process.stderr)
        self.assertEqual(self.server.load_state()['runs'][0]['status'], 'COMPLETE')

    def test_operator_cli_missing_token_is_sanitized(self):
        self.queue()
        process = subprocess.run(self.worker_command(), cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)['state'], 'ADAPTER_FAILED')
        self.assertNotIn('Traceback', process.stderr)
        self.assertFalse(self.output.exists())


if __name__ == '__main__': unittest.main()
