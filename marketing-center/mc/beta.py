"""One-command synthetic beta fixture, isolated to a new local output directory."""
import argparse
import hashlib
from http.server import ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import secrets
import threading
from .command_center import LocalCommandCenter, request_binding
from .core import ROOT
from .supervised import shadow_supervised


def main():
    parser=argparse.ArgumentParser(description='Run isolated synthetic Salem beta; never publish or spend')
    parser.add_argument('--command-center',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    http=None
    thread=None
    keys=('ZENTRYVA_CONTROL_TOKEN','ZENTRYVA_WORKER_TOKENS')
    previous={k:os.environ.get(k) for k in keys}
    try:
        pin=json.loads((ROOT/'contracts/local-command-center.json').read_text(encoding='utf-8'))
        for name,expected in pin['files'].items():
            if Path(name).name!=name: raise ValueError('Invalid shared source pin')
            actual=hashlib.sha256((args.command_center/name).read_text(encoding='utf-8').encode('utf-8')).hexdigest()
            if actual!=expected: raise ValueError('Shared source differs from qualified beta')
        data=json.loads((ROOT/'fixtures/salem-shadow.json').read_text(encoding='utf-8'))
        at=data['analytics']['observed_at']
        binding=request_binding(data,at)
        output=args.output.resolve()
        output.mkdir(parents=True,exist_ok=False)
        spec=importlib.util.spec_from_file_location('salem_beta_cc',args.command_center/'server.py')
        server=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)
        server.DATA=output/'command-center'
        server.DATA.mkdir()
        server.STATE=server.DATA/'state.json'
        server.EVENTS=server.DATA/'events.jsonl'
        server.EVENTS.touch()
        server.STATE.write_text(json.dumps(dict(settings={'stall_after_seconds':900},
            projects=[dict(id='salem-beta',desired_state='RUNNING',status='RUNNING',assigned_worker_id='beta-worker')],
            workers=[dict(id='beta-worker',state='IDLE',current_project_id='salem-beta')],
            providers=[dict(id='synthetic-local',enabled=True)],runs=[],attention=[])),encoding='utf-8')
        owner_token,worker_token=secrets.token_hex(32),secrets.token_hex(32)
        os.environ['ZENTRYVA_CONTROL_TOKEN']=owner_token
        os.environ['ZENTRYVA_WORKER_TOKENS']=json.dumps({'beta-worker':worker_token})
        class QuietHandler(server.Handler):
            def log_message(self,*args): pass
        http=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        thread=threading.Thread(target=http.serve_forever,daemon=True)
        thread.start()
        url=f'http://127.0.0.1:{http.server_port}'
        # Fixture provisioning is explicitly local. The runtime worker below
        # receives only its worker token, never the owner token.
        controller=LocalCommandCenter(url,'beta-worker',owner_token)
        controller.request('/api/execution/request',dict(run_id='salem-beta-run',
            project_id='salem-beta',worker_id='beta-worker',provider_id='synthetic-local',
            action='marketing.shadow.verify',protocol='cooperative-v1',input=binding))
        client=LocalCommandCenter(url,'beta-worker',worker_token)
        result=shadow_supervised(client=client,run_id='salem-beta-run',project_id='salem-beta',
            provider_id='synthetic-local',tenant_id=data['tenant']['tenant_id'],data=data,
            output_root=output/'marketing',now=at)
        summary=dict(state=result['state'],run_id=result['run_id'],production_published=False,cost_usd=0,
                     dashboard=str(Path(result['output_dir'])/'dashboard.html'),
                     shared_source=pin,marketing_runtime=result['runtime'],
                     qualification='SYNTHETIC LOCAL BETA ONLY',fixture_clock=at)
        (output/'beta-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(json.dumps(summary))
        return 0 if result['state']=='SHADOW_COMPLETE' else 1
    except Exception:
        print(json.dumps(dict(state='BETA_FAILED',message='Preserve output; verify qualified sources and use a new output directory')))
        return 2
    finally:
        if http:
            if thread: http.shutdown()
            http.server_close()
        if thread: thread.join()
        for key,value in previous.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value


if __name__=='__main__':
    raise SystemExit(main())
