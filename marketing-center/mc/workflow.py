"""A deterministic, file-based shadow loop. It never calls a publishing API."""
import html
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from .core import digest, record, scoped, number, timestamp, validate, runtime_provenance
from .catalog import configured_registry
# Compatibility exports for existing local consumers.
from .stages import review, delivery, normalize, attribute, learn, _brand

def run(data, output_root, now):
    if data.get('mode','shadow')!='shadow':
        raise ValueError('Only shadow mode is implemented; MC-017 gates production')
    tenant=data['tenant'];validate('schemas/tenant.schema.json',tenant)
    tenant_id=tenant['tenant_id'];objective=data['objective']
    if objective not in tenant['objectives']:
        raise ValueError('Objective not authorized by tenant configuration')
    timestamp(now)
    scoped(tenant_id,[data['brand'],data['baseline']]+([data['analytics']] if data.get('analytics') else []))
    _brand(data['brand'])
    if data.get('analytics') and (data['analytics'].get('spend') != 0 or data['analytics'].get('source_type')!='synthetic'):
        raise ValueError('No-spend shadow loop accepts synthetic metrics only')
    if 'modules' in data and not isinstance(data['modules'],dict):
        raise ValueError('Module selection must be an object')
    registry=configured_registry(tenant_id, data.get('modules'))
    runtime=runtime_provenance()
    runtime['modules']=registry.snapshot()
    run_id='run-'+digest(dict(inputs=data,now=now,source_sha256=runtime['source_sha256'],python=runtime['python'],jsonschema=runtime['jsonschema'],modules=runtime['modules']))[:20]
    target=Path(output_root).resolve()/tenant_id/run_id
    if target.exists():
        manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        replay=json.loads((target/'result.json').read_text(encoding='utf-8'))
        expected_files={'result.json','inputs.json','records.jsonl','command-center-status.json','dashboard.html'}
        if replay.get('publication'):
            expected_files.add('handoff.md')
        if (manifest.get('run_id')!=run_id or replay.get('run_id')!=run_id
                or manifest.get('runtime',{}).get('source_sha256')!=runtime['source_sha256']
                or manifest.get('runtime',{}).get('modules')!=runtime['modules']
                or set(manifest.get('files',{}))!=expected_files):
            raise ValueError('Evidence manifest identity or inventory mismatch')
        for name,expected in manifest['files'].items():
            if Path(name).name!=name or digest((target/name).read_text(encoding='utf-8'))!=expected:
                raise ValueError('Existing evidence modified; preserve and investigate')
        replay['output_dir']=str(target)
        return replay
    evidence=registry.call('intelligence','research',objective,data['sources'],now)
    rivals=registry.call('intelligence','competitors',objective,evidence,now)
    decision=registry.call('intelligence','strategy',objective,evidence,rivals,now)
    result=dict(run_id=run_id,tenant_id=tenant_id,mode='shadow',production_published=False,
        cost_usd=0,output_dir=str(target),runtime=runtime,evidence=evidence,competitors=rivals,strategy=decision)
    records=evidence+rivals+[decision]
    if decision['action']=='HOLD':
        result['state']='EVIDENCE_HOLD'
    else:
        campaign=registry.call('planning','campaign',objective,decision,now)
        brand=data['brand']
        content=registry.call('content','create',objective,decision,campaign,brand,now)
        gate=registry.call('content','review',objective,content,brand,now)
        result.update(campaign=campaign,content=content,review=gate)
        records += [campaign,content,gate]
        if gate['state']=='REJECTED':
            result['state']='REVIEW_BLOCKED'
        else:
            publication=registry.call('publishing','handoff',objective,decision,campaign,content,gate,now)
            delivered=registry.call('publishing','delivery',objective,publication,None,now)
            result.update(publication=publication,delivery=delivered)
            records += [publication,delivered]
            if data.get('analytics') is None:
                result['state']='WAITING_ANALYTICS'
            else:
                metric=registry.call('measurement','normalize',objective,data['analytics'],campaign['campaign_id'],now)
                attribution=registry.call('measurement','attribute',objective,metric,now)
                learning=registry.call('optimization','learn',objective,metric,data['baseline'],data['window_days'],now)
                experiment,next_decision,memory=registry.call('optimization','next',objective,decision,campaign,brand,data['baseline'],learning,now)
                records += [metric,attribution,learning,experiment,next_decision,memory]
                result.update(state='SHADOW_COMPLETE',metrics=metric,attribution=attribution,learning=learning,
                    experiment=experiment,next_strategy=next_decision,memory=memory)
    status=dict(work_id='MC-R1-'+tenant_id,tenant_id=tenant_id,component='shadow-loop',
        state='VERIFIED' if result['state']=='SHADOW_COMPLETE' else 'READY',updated_at=now,heartbeat_at=now,
        cost_usd=0,blocker_id=None,evidence_refs=[r['record_id'] for r in records],
        message=result['state']+'; local adapter only; Command Center integration UNVERIFIED; MC-017 isolated')
    validate('contracts/command-center-interface.schema.json',status)
    for item in records:
        validate('schemas/marketing-record.schema.json',item)
    result['status']=status
    _persist(target,result,records,data)
    return result

def _persist(target,result,records,inputs):
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.pending-',dir=target.parent))
    try:
        files={'result.json':json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),
               'inputs.json':json.dumps(inputs,indent=2,ensure_ascii=False,allow_nan=False),
               'records.jsonl':'\n'.join(json.dumps(r,ensure_ascii=False,allow_nan=False) for r in records)+'\n',
               'command-center-status.json':json.dumps(result['status'],indent=2)}
        content=result.get('content',{})
        if result.get('publication'):
            files['handoff.md']='# SHADOW ONLY — NOT APPROVED FOR PUBLICATION\n\n'+content['copy']+'\n\nCTA: '+content['cta']+'\n\n'+content['tracking_url']+'\n\nMC-017 requires owner approval, actual brand/product facts, baseline and access.\n'
        sections=''.join('<section><h2>'+html.escape(k.replace('_',' ').title())+'</h2><pre>'+html.escape(json.dumps(v,indent=2,ensure_ascii=False))+'</pre></section>' for k,v in result.items() if isinstance(v,(dict,list)))
        files['dashboard.html']='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Marketing Center shadow review</title><style>body{font:16px system-ui;background:#101820;color:#eaf4ed;max-width:1100px;margin:40px auto;padding:20px}h1{color:#9bdeb4}section{background:#1c2932;padding:20px;margin:16px 0;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px monospace}.flag{color:#ffd185}</style><h1>Marketing Center — '+html.escape(result['tenant_id'])+'</h1><p class="flag">SYNTHETIC SHADOW • $0 spend • Nothing published • Live integrations unverified</p><h2>'+html.escape(result['state'])+'</h2>'+sections+'</html>'
        for name,text in files.items():
            (temp/name).write_text(text,encoding='utf-8')
        (temp/'manifest.json').write_text(json.dumps(dict(run_id=result['run_id'],runtime=result['runtime'],hash_method='SHA256 of canonical JSON string of UTF-8 text',files={name:digest(text) for name,text in files.items()}),indent=2),encoding='utf-8')
        # Rename publishes a complete evidence directory, never a partially written run.
        os.rename(temp,target)
    finally:
        if temp.exists(): shutil.rmtree(temp)
