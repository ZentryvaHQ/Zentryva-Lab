"""Structured evidence imports; no scraping, provider calls or invented observations."""
from urllib.parse import urlsplit
from .core import record, scoped, number, timestamp, digest

def research(tenant, objective, sources, now):
    scoped(tenant, sources)
    seen = set()
    result = []
    for source in sources:
        for key in ('source_id', 'source_uri', 'finding', 'applicability', 'channel', 'format'):
            if not isinstance(source.get(key), str) or not source[key].strip():
                raise ValueError('Missing evidence field: ' + key)
        if source['source_id'] in seen:
            raise ValueError('Duplicate evidence identity')
        seen.add(source['source_id'])
        uri = urlsplit(source['source_uri'])
        if uri.scheme != 'https' or not uri.hostname or uri.username or uri.password:
            raise ValueError('Public HTTPS source reference required')
        if source.get('source_type') not in ('synthetic', 'public_observation', 'authorized_client_data'):
            raise ValueError('Unknown source type')
        age = (timestamp(now)-timestamp(source.get('observed_at'))).total_seconds()/86400
        if age < 0:
            raise ValueError('Future observation')
        confidence=number(source.get('confidence'),0,1)
        relevance=number(source.get('relevance'),0,1)
        item=record(tenant,'research',objective,now,confidence=confidence,
                    source_id=source['source_id'],source_sha256=digest(source),
                    finding=source['finding'],applicability=source['applicability'],
                    age_days=age,channel=source['channel'],format=source['format'],
                    competitor=source.get('competitor'),positioning=source.get('positioning'),
                    offers=source.get('offers',[]),reactions=source.get('reactions',[]),
                    limitations=source.get('limitations',[]))
        item['provenance']=dict(source_type=source['source_type'],source_uri=source['source_uri'],
            observed_at=source['observed_at'],freshness='fresh' if age <= 30 else 'stale',
            relevance=relevance,confidence=confidence)
        result.append(item)
    return result

def competitors(tenant, objective, evidence, now):
    scoped(tenant,evidence,objective)
    return [record(tenant,'competitor',objective,now,[e['record_id']],
                name=e['competitor'],channels=[e['channel']],formats=[e['format']],
                positioning=e['positioning'],offers=e['offers'],reactions=e['reactions'],
                observed_patterns=[e['finding']],limitations=e['limitations'],
                confidence=e['provenance']['confidence']) for e in evidence if e.get('competitor')]

def strategy(tenant, objective, evidence, competitor_records, now):
    scoped(tenant,evidence+competitor_records,objective)
    eligible=[e for e in evidence if e['provenance']['freshness']=='fresh'
              and e['provenance']['confidence'] >= .5 and e['provenance']['relevance'] >= .5
              and e['channel'] in ('website','email')]
    eligible.sort(key=lambda e:(-e['provenance']['confidence']*e['provenance']['relevance'], e['record_id']))
    if not eligible:
        return record(tenant,'strategy',objective,now,action='HOLD',reason='No fresh, relevant evidence for an allowed shadow channel',channel=None)
    chosen=eligible[0]
    return record(tenant,'strategy',objective,now,[chosen['record_id']]+[c['record_id'] for c in competitor_records],
        action='EXPERIMENT',channel=chosen['channel'],format=chosen['format'],
        opportunity=chosen['finding'],audience=chosen['applicability'],
        reason='Highest confidence × relevance among fresh evidence for allowed channels; test the information gap',
        confidence=chosen['provenance']['confidence'],expected_outcome='More qualified visits and leads',
        risk='Observed patterns may not generalize; no causal claim',measurement='Qualified leads per tracked visit against comparable baseline',
        cadence='One controlled experiment; reassess after measurement, no recurring publishing schedule',
        budget_recommendation_usd=0,synthetic=any(e['provenance']['source_type']=='synthetic' for e in eligible))
