"""A deterministic, file-based shadow loop. It never calls a publishing API."""
import html
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from .core import digest, record, scoped, number, timestamp, validate
from .intelligence import research, competitors, strategy

def review(tenant, objective, content, brand, now):
    scoped(tenant,[content,brand])
    reasons=[]
    if brand.get('status') != 'SYNTHETIC_SHADOW_PROFILE':
        reasons.append('Brand profile not approved for this shadow fixture')
    if brand.get('sensitive_targeting') is not False:
        reasons.append('Sensitive targeting prohibited')
    copy=content['copy'].casefold()
    terms=set(brand.get('forbidden_terms',[])) | {'guaranteed cure','treats cancer','cures cancer'}
    if any(term.casefold() in copy for term in terms):
        reasons.append('Prohibited claim')
    if brand['name'].casefold() not in copy or content['copy'] != brand['approved_copy']:
        reasons.append('Copy outside supplied brand allowlist')
    return record(tenant,'review',objective,now,[content['record_id']],
                  state='REJECTED' if reasons else 'SHADOW_REVIEW_PASSED',reasons=reasons,
                  production_approved=False,limitation='Mechanical fixture gate; human brand/compliance review required before any live use')

def delivery(tenant, objective, publication, receipt, now):
    scoped(tenant,[publication])
    if receipt and receipt.get('tenant_id',tenant) != tenant:
        raise ValueError('Cross-tenant receipt')
    state='NOT_PUBLISHED'
    if receipt:
        state='UNVERIFIED'
        if receipt.get('error'):
            state={'expired_auth':'AUTH_EXPIRED','rate_limit':'RETRY_REQUIRED','missing_post':'MISSING_PUBLICATION'}.get(receipt['error'],'FAILED')
        elif receipt.get('published') and receipt.get('rendered') and receipt.get('tracking') is False:
            state='TRACKING_FAILED'
        # The local adapter cannot verify public rendering; receipts alone never promote to VERIFIED.
    return record(tenant,'delivery',objective,now,[publication['record_id']],
        campaign_id=publication['campaign_id'],content_id=publication['content_id'],state=state,
        receipt=receipt,production_verified=False,
        recovery='Command Center retry/human verification required' if state not in ('NOT_PUBLISHED','UNVERIFIED') else None)

def normalize(tenant, objective, raw, campaign_id, now):
    scoped(tenant,[raw])
    if raw.get('source_type') not in ('synthetic','authorized_client_data'):
        raise ValueError('Metric provenance required')
    if timestamp(raw.get('observed_at')) > timestamp(now):
        raise ValueError('Future metrics')
    uri=urlsplit(raw.get('source_uri',''))
    if uri.scheme != 'https' or not uri.hostname or uri.username or uri.password:
        raise ValueError('Metric source required')
    values={key:number(raw.get(key)) for key in ('visits','leads','conversions','revenue','spend')}
    for key in ('visits','leads','conversions'):
        if not isinstance(values[key],int):
            raise ValueError('Integer count required')
    if values['leads'] > values['visits']:
        raise ValueError('Leads exceed visits in this funnel')
    if raw.get('attribution_evidence') not in ('none','temporal','survey','tracked'):
        raise ValueError('Unknown attribution evidence')
    tracked=number(raw.get('tracked_revenue',0))
    if tracked>values['revenue']:
        raise ValueError('Tracked revenue exceeds total')
    ids=raw.get('verified_conversion_ids',[])
    if not isinstance(ids,list) or any(not isinstance(i,str) or not i.strip() for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Invalid conversion evidence')
    item=record(tenant,'metric',objective,now,campaign_id=campaign_id,**values,
        attribution_evidence=raw['attribution_evidence'],tracking_campaign_id=raw.get('tracking_campaign_id'),
        verified_conversion_ids=ids,tracked_revenue=tracked,synthetic=raw['source_type']=='synthetic',source_sha256=digest(raw))
    item['provenance'].update(source_type=raw['source_type'],source_uri=raw['source_uri'],observed_at=raw['observed_at'])
    return item

def attribute(tenant, objective, metric, now):
    scoped(tenant,[metric],objective)
    classification={'none':'UNKNOWN','temporal':'CORRELATED','survey':'LIKELY_INFLUENCED','tracked':'UNKNOWN'}[metric['attribution_evidence']]
    revenue=None
    if metric['attribution_evidence']=='tracked' and metric['tracking_campaign_id']==metric['campaign_id'] and metric['verified_conversion_ids']:
        classification='DIRECTLY_ATTRIBUTED'
        revenue=metric['tracked_revenue']
    return record(tenant,'attribution',objective,now,[metric['record_id']],campaign_id=metric['campaign_id'],
        classification=classification,attributed_revenue=revenue,
        roas=revenue/metric['spend'] if revenue is not None and metric['spend']>0 else None,
        synthetic=metric['synthetic'],causality_proven=False)

def learn(tenant, objective, metric, baseline, window_days, now):
    scoped(tenant,[metric,baseline])
    visits=number(baseline.get('visits'));leads=number(baseline.get('leads'))
    if leads>visits:
        raise ValueError('Invalid baseline funnel')
    number(window_days,1);number(baseline.get('window_days'),1)
    comparable=baseline['window_days']==window_days and baseline.get('source_type')==('synthetic' if metric['synthetic'] else 'authorized_client_data')
    sufficient=comparable and visits>=30 and metric['visits']>=30
    delta=round(metric['leads']/metric['visits']-leads/visits,6) if sufficient else None
    recommendation='HOLD' if delta is None else ('REDUCE' if delta<0 else 'EXPERIMENT')
    return record(tenant,'learning',objective,now,[metric['record_id']],campaign_id=metric['campaign_id'],
        baseline_sha256=digest(baseline),lead_rate_delta=delta,recommendation=recommendation,
        reason='Insufficient/comparability-limited data' if delta is None else 'Observed lead-rate change; test a CTA variant before scaling',
        confidence=.3 if sufficient else 0,spend_recommendation_usd=0,causal_claim=False,
        measurement='Compare qualified lead rate in equal observation windows',
        risk='No randomized control; changes are not proof of causation',synthetic=metric['synthetic'])

def _brand(brand):
    for key in ('name','approved_copy','cta','landing_url'):
        if not isinstance(brand.get(key),str) or not brand[key].strip():
            raise ValueError('Missing brand field: '+key)
    parsed=urlsplit(brand['landing_url'])
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('HTTPS landing URL required')
    if not isinstance(brand.get('forbidden_terms'),list) or any(not isinstance(t,str) or not t for t in brand['forbidden_terms']):
        raise ValueError('Forbidden terms must be nonempty strings')

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
    run_id='run-'+digest(dict(inputs=data,now=now))[:20]
    target=Path(output_root).resolve()/tenant_id/run_id
    if target.exists():
        manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        for name,expected in manifest['files'].items():
            if Path(name).name!=name or digest((target/name).read_text(encoding='utf-8'))!=expected:
                raise ValueError('Existing evidence modified; preserve and investigate')
        return json.loads((target/'result.json').read_text(encoding='utf-8'))
    evidence=research(tenant_id,objective,data['sources'],now)
    rivals=competitors(tenant_id,objective,evidence,now)
    decision=strategy(tenant_id,objective,evidence,rivals,now)
    result=dict(run_id=run_id,tenant_id=tenant_id,mode='shadow',production_published=False,
        cost_usd=0,output_dir=str(target),evidence=evidence,competitors=rivals,strategy=decision)
    records=evidence+rivals+[decision]
    if decision['action']=='HOLD':
        result['state']='EVIDENCE_HOLD'
    else:
        campaign=record(tenant_id,'campaign',objective,now,[decision['record_id']],
            audience=decision['audience'],platform=decision['channel'],format=decision['format'],
            hypothesis='Answering the evidenced information gap will improve qualified lead rate',
            budget_usd=0,schedule='Await human selection after shadow review')
        campaign['campaign_id']=campaign['record_id']
        brand=data['brand'];parts=urlsplit(brand['landing_url'])
        query=[(k,v) for k,v in parse_qsl(parts.query) if not k.startswith('utm_')]
        query += [('utm_source',decision['channel']),('utm_medium','organic'),('utm_campaign',campaign['campaign_id'])]
        tracked_url=urlunsplit(parts._replace(query=urlencode(query)))
        content=record(tenant_id,'content',objective,now,[campaign['record_id']],campaign_id=campaign['campaign_id'],
            platform=decision['channel'],format=decision['format'],audience=decision['audience'],
            copy=brand['approved_copy'],cta=brand['cta'],tracking_url=tracked_url,
            creative_brief='Use a text-first FAQ with approved product information; no unsupported benefit claims. Human-selected approved imagery only.',
            generation_method='Allowlisted template; no paid AI provider',synthetic=True)
        content['content_id']=content['record_id']
        gate=review(tenant_id,objective,content,brand,now)
        result.update(campaign=campaign,content=content,review=gate)
        records += [campaign,content,gate]
        if gate['state']=='REJECTED':
            result['state']='REVIEW_BLOCKED'
        else:
            publication=record(tenant_id,'publication',objective,now,[content['record_id'],gate['record_id']],
                campaign_id=campaign['campaign_id'],content_id=content['content_id'],platform=decision['channel'],
                adapter='manual-shadow',state='HANDOFF_READY',idempotency_key=digest([tenant_id,content['record_id']]),
                production_approved=False)
            delivered=delivery(tenant_id,objective,publication,None,now)
            result.update(publication=publication,delivery=delivered)
            records += [publication,delivered]
            if data.get('analytics') is None:
                result['state']='WAITING_ANALYTICS'
            else:
                metric=normalize(tenant_id,objective,data['analytics'],campaign['campaign_id'],now)
                attribution=attribute(tenant_id,objective,metric,now)
                learning=learn(tenant_id,objective,metric,data['baseline'],data['window_days'],now)
                experiment=record(tenant_id,'experiment',objective,now,[campaign['record_id'],learning['record_id']],
                    campaign_id=campaign['campaign_id'],variable='CTA',control=brand['cta'],
                    variant='Ask a product question',state='PROPOSED',success_metric='qualified leads / visits',
                    baseline=data['baseline'],minimum_visits_per_arm=30,
                    limitation='No experiment has been run; threshold is a screening floor, not statistical significance')
                next_decision=record(tenant_id,'strategy',objective,now,[decision['record_id'],learning['record_id'],experiment['record_id']],
                    action=learning['recommendation'],channel=decision['channel'],
                    reason=learning['reason'],next_test=experiment['record_id'],budget_recommendation_usd=0)
                memory=record(tenant_id,'memory',objective,now,[learning['record_id'],next_decision['record_id']],
                    memory_type='CAMPAIGN_MEMORY',scope='tenant_only',lesson=learning['reason'],synthetic=True)
                records += [metric,attribution,learning,experiment,next_decision,memory]
                result.update(state='SHADOW_COMPLETE',metrics=metric,attribution=attribution,learning=learning,
                    experiment=experiment,next_strategy=next_decision,memory=memory)
    status=dict(work_id='MC-R1-SALEM-001',tenant_id=tenant_id,component='shadow-loop',
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
        files['dashboard.html']='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Salem shadow review</title><style>body{font:16px system-ui;background:#101820;color:#eaf4ed;max-width:1100px;margin:40px auto;padding:20px}h1{color:#9bdeb4}section{background:#1c2932;padding:20px;margin:16px 0;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px monospace}.flag{color:#ffd185}</style><h1>Marketing Center — '+html.escape(result['tenant_id'])+'</h1><p class="flag">SYNTHETIC SHADOW • $0 spend • Nothing published • Live integrations unverified</p><h2>'+html.escape(result['state'])+'</h2>'+sections+'</html>'
        for name,text in files.items():
            (temp/name).write_text(text,encoding='utf-8')
        (temp/'manifest.json').write_text(json.dumps(dict(run_id=result['run_id'],files={name:digest(text) for name,text in files.items()}),indent=2),encoding='utf-8')
        # Rename publishes a complete evidence directory, never a partially written run.
        os.rename(temp,target)
    finally:
        if temp.exists(): shutil.rmtree(temp)
