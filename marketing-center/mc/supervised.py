"""Cooperative local shadow worker; the shared control plane owns run authority.

Only bundled pure stages run here. Checks occur at stage boundaries, not inside
arbitrary provider code. No HTTP mutation is blindly retried.
"""
from copy import deepcopy
import json
from pathlib import Path
import secrets
from urllib.parse import urlencode
from .command_center import request_binding, _ID, _REF
from .core import digest
from .recovery import Journal
from .workflow import run


class Suspended(ValueError):
    pass


class ControlUnavailable(ValueError):
    pass


def _reconcile(view,binding,root):
    summary=view.get('result',{})
    identity=summary.get('shadow_run_id','')
    if (summary.get('request_binding')!=binding or not _ID.fullmatch(identity)
            or summary.get('state')!='SHADOW_COMPLETE'
            or summary.get('production_published') is not False or summary.get('cost_usd')!=0):
        raise ValueError('Terminal run requires explicit failure diagnosis')
    target=Path(root).resolve()/binding['tenant_id']/identity
    manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    if (digest(manifest)!=summary.get('manifest_sha256')
            or manifest.get('files')!=summary.get('files')
            or manifest.get('run_id')!=identity
            or manifest.get('runtime',{}).get('source_sha256')!=binding['source_sha256']):
        raise ValueError('Terminal evidence does not match shared result')
    for name,expected in manifest['files'].items():
        if Path(name).name!=name or digest((target/name).read_text(encoding='utf-8'))!=expected:
            raise ValueError('Terminal artifact integrity failed')
    result=json.loads((target/'result.json').read_text(encoding='utf-8'))
    if result.get('run_id')!=identity or result.get('tenant_id')!=binding['tenant_id']:
        raise ValueError('Terminal identity mismatch')
    result['output_dir']=str(target)
    return result


def shadow_supervised(*,client,run_id,project_id,provider_id,tenant_id,data,output_root,now):
    data=deepcopy(data)
    for identity in (run_id,project_id,provider_id,tenant_id):
        if not isinstance(identity,str) or not _ID.fullmatch(identity):
            raise ValueError('Invalid job identity')
    binding=request_binding(data,now)
    if binding['tenant_id']!=tenant_id: raise ValueError('Local tenant binding mismatch')
    owner=dict(worker_id=client.worker_id,run_id=run_id)
    view=client.request('/api/execution/status?'+urlencode(owner))
    selected=view.get('run',{})
    expected=dict(id=run_id,worker_id=client.worker_id,project_id=project_id,provider_id=provider_id,
                  protocol='cooperative-v1',action='marketing.shadow.verify',
                  requires_owner_approval=False,input=binding)
    if any(selected.get(k)!=v for k,v in expected.items()):
        raise ValueError('Selected run does not match authorized local shadow request')
    if selected.get('status') in {'COMPLETE','FAILED'}:
        return _reconcile(view,binding,output_root)
    if selected.get('status') not in {'QUEUED','RUNNING'}:
        raise ValueError('Selected run is not executable')
    if view.get('runnable') is not True:
        return dict(state='SUSPENDED',run_id=run_id,production_published=False,cost_usd=0)
    session=dict(**owner,session_id=secrets.token_hex(16))
    lock=Path(output_root)/'.sessions'/digest([run_id,client.port,client.worker_id])
    with Journal(lock):
        payload=dict(session)
        if selected['status']=='QUEUED':
            payload['receipt_ref']=client.evidence(run_id,'receipt',dict(adapter='marketing-cooperative-v1',**binding))
            payload['checkpoint_ref']=client.evidence(run_id,'checkpoint',dict(state='BEFORE_LOCAL_SHADOW',**binding))
        acquired=client.request('/api/execution/acquire',payload)
        if acquired.get('run',{}).get('status')!='RUNNING':
            raise ValueError('Acquisition state mismatch')

        def control():
            try:
                response=client.request('/api/execution/pulse',session)
            except ValueError:
                raise ControlUnavailable('Shared control unavailable; preserve checkpoints') from None
            if response.get('runnable') is not True: raise Suspended('Shared control suspended run')

        def finish(status,summary):
            control()
            reply=client.request('/api/evidence',dict(**session,kind='result',evidence=summary))
            ref=reply.get('evidence_ref','')
            if not isinstance(ref,str) or not _REF.fullmatch(ref): raise ValueError('Invalid result reference')
            done=client.request('/api/execution/complete',dict(**session,status=status,evidence_ref=ref))
            if done.get('run',{}).get('status')!=status: raise ValueError('Completion mismatch')

        try:
            try:
                result=run(data,output_root,now,control=control)
            except (Suspended,ControlUnavailable):
                raise
            except Exception:
                finish('FAILED',dict(state='LOCAL_SHADOW_FAILED',request_binding=binding))
                raise ValueError('Local shadow failed; checkpoints preserved') from None
            manifest=json.loads((Path(result['output_dir'])/'manifest.json').read_text(encoding='utf-8'))
            summary=dict(shadow_run_id=result['run_id'],state=result['state'],tenant_id=tenant_id,
                         production_published=False,cost_usd=0,request_binding=binding,
                         manifest_sha256=digest(manifest),files=manifest['files'])
            finish('COMPLETE' if result['state']=='SHADOW_COMPLETE' else 'FAILED',summary)
            return result
        except Suspended:
            return dict(state='SUSPENDED',run_id=run_id,production_published=False,cost_usd=0)
        finally:
            # Best effort only; a lost response leaves a bounded lease, never
            # authorizes a blind retry or another worker's completion.
            try: client.request('/api/execution/release',session)
            except ValueError: pass
