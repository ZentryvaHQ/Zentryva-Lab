"""Bundled marketing capabilities; no shared scheduling or provider infrastructure."""
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from .core import digest, record, scoped, number, timestamp

def review(tenant, objective, content, brand, now):
    scoped(tenant,[content,brand])
    reasons=[]
    if brand.get('status') != 'SYNTHETIC_SHADOW_PROFILE':
        reasons.append('Brand profile not approved for this shadow fixture')
    if brand.get('sensitive_targeting') is not False:
        reasons.append('Sensitive targeting prohibited')
    copy=' '.join(str(content.get(key,'')) for key in ('copy','cta','creative_brief','tracking_url','audience')).casefold()
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
    if receipt is not None:
        if not isinstance(receipt,dict) or any(receipt.get(key)!=publication.get(key) for key in ('tenant_id','campaign_id','content_id')):
            raise ValueError('Receipt identity mismatch')
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
    if raw.get('campaign_id',campaign_id)!=campaign_id or raw.get('objective',objective)!=objective:
        raise ValueError('Metric campaign or objective mismatch')
    if raw.get('source_type') not in ('synthetic','authorized_client_data'):
        raise ValueError('Metric provenance required')
    if raw['source_type'] != 'synthetic' and raw.get('campaign_id')!=campaign_id:
        raise ValueError('Explicit campaign binding required for imported client metrics')
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
    if values['conversions'] > values['visits']:
        raise ValueError('Conversions exceed visits in this funnel')
    if raw.get('attribution_evidence') not in ('none','temporal','survey','tracked'):
        raise ValueError('Unknown attribution evidence')
    tracked=number(raw.get('tracked_revenue',0))
    if tracked>values['revenue']:
        raise ValueError('Tracked revenue exceeds total')
    ids=raw.get('verified_conversion_ids',[])
    if not isinstance(ids,list) or any(not isinstance(i,str) or not i.strip() for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Invalid conversion evidence')
    if len(ids)>values['conversions']:
        raise ValueError('Conversion references exceed measured conversions')
    item=record(tenant,'metric',objective,now,[campaign_id],campaign_id=campaign_id,**values,
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
    if baseline.get('objective',objective)!=objective:
        raise ValueError('Baseline objective mismatch')
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


def plan_campaign(tenant, objective, decision, now):
    scoped(tenant,[decision],objective)
    campaign=record(tenant,'campaign',objective,now,[decision['record_id']],
        audience=decision['audience'],platform=decision['channel'],format=decision['format'],
        hypothesis='Answering the evidenced information gap will improve qualified lead rate',
        budget_usd=0,schedule='Await human selection after shadow review')
    campaign['campaign_id']=campaign['record_id']
    return campaign

def create_content(tenant, objective, decision, campaign, brand, now):
    scoped(tenant,[decision,campaign],objective); scoped(tenant,[brand]); _brand(brand)
    parts=urlsplit(brand['landing_url'])
    query=[(k,v) for k,v in parse_qsl(parts.query) if not k.startswith('utm_')]
    query += [('utm_source',decision['channel']),('utm_medium','organic'),('utm_campaign',campaign['campaign_id'])]
    tracked_url=urlunsplit(parts._replace(query=urlencode(query)))
    content=record(tenant,'content',objective,now,[campaign['record_id']],campaign_id=campaign['campaign_id'],
        platform=decision['channel'],format=decision['format'],audience=decision['audience'],
        copy=brand['approved_copy'],cta=brand['cta'],tracking_url=tracked_url,
        creative_brief='Use a text-first FAQ with approved product information; no unsupported benefit claims. Human-selected approved imagery only.',
        generation_method='Allowlisted template; no paid AI provider',synthetic=True)
    content['content_id']=content['record_id']
    return content

def handoff(tenant, objective, decision, campaign, content, gate, now):
    scoped(tenant,[decision,campaign,content,gate],objective)
    if gate.get('state')!='SHADOW_REVIEW_PASSED' or gate.get('evidence_refs')!=[content['record_id']]:
        raise ValueError('Reviewed content required')
    publication=record(tenant,'publication',objective,now,[content['record_id'],gate['record_id']],
        campaign_id=campaign['campaign_id'],content_id=content['content_id'],platform=decision['channel'],
        adapter='manual-shadow',state='HANDOFF_READY',idempotency_key=digest([tenant,content['record_id']]),
        production_approved=False)
    return publication

def optimize(tenant, objective, decision, campaign, brand, baseline, learning, now):
    scoped(tenant,[decision,campaign,learning],objective); scoped(tenant,[brand,baseline])
    experiment=record(tenant,'experiment',objective,now,[campaign['record_id'],learning['record_id']],
        campaign_id=campaign['campaign_id'],variable='CTA',control=brand['cta'],
        variant='Ask a product question',state='PROPOSED',success_metric='qualified leads / visits',
        baseline=baseline,minimum_visits_per_arm=30,
        limitation='No experiment has been run; threshold is a screening floor, not statistical significance')
    next_decision=record(tenant,'strategy',objective,now,[decision['record_id'],learning['record_id'],experiment['record_id']],
        action=learning['recommendation'],channel=decision['channel'],
        reason=learning['reason'],next_test=experiment['record_id'],budget_recommendation_usd=0)
    memory=record(tenant,'memory',objective,now,[learning['record_id'],next_decision['record_id']],
        memory_type='CAMPAIGN_MEMORY',scope='tenant_only',lesson=learning['reason'],synthetic=True)
    return (experiment,next_decision,memory)
