"""One-shot local qualification adapter for the shared Command Center protocol.

This is not a supervisor. It cannot resume an acknowledged remote run, observe
owner pause requests, or publish marketing content. No automatic HTTP retries.
"""
from copy import deepcopy
import http.client
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit
from .core import digest, runtime_provenance, timestamp, validate
from .input_safety import check_input
from .workflow import run

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
_REF = re.compile(r'sha256:[0-9a-f]{64}\Z')


class LocalCommandCenter:
    """Worker-token transport restricted to literal IPv4 loopback; no proxies."""
    def __init__(self, base_url, worker_id, token):
        url = urlsplit(base_url)
        if (url.scheme != 'http' or url.hostname != '127.0.0.1' or url.port is None
                or url.username or url.password or url.path or url.query or url.fragment):
            raise ValueError('Explicit local loopback endpoint required')
        if not isinstance(worker_id, str) or not _ID.fullmatch(worker_id):
            raise ValueError('Invalid worker identity')
        if not isinstance(token, str) or not token or any(c.isspace() for c in token):
            raise ValueError('Worker token required')
        self.port, self.worker_id, self._token = url.port, worker_id, token

    def request(self, path, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            encoded = None if body is None else json.dumps(body, allow_nan=False).encode('utf-8')
            if encoded is not None and len(encoded) > 65536:
                raise ValueError('Request too large')
            conn.request('GET' if body is None else 'POST', path, body=encoded,
                headers={'Authorization':'Bearer '+self._token, 'Content-Type':'application/json'})
            response = conn.getresponse()
            raw = response.read(262145)
            if response.status not in (200, 201) or len(raw) > 262144:
                raise ValueError('Rejected response')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError('Invalid response')
            return result
        except Exception:
            # Never propagate token-bearing request details or untrusted response text.
            raise ValueError('Command Center request failed') from None
        finally:
            conn.close()

    def evidence(self, run_id, kind, value):
        result = self.request('/api/evidence', dict(run_id=run_id, worker_id=self.worker_id,
                                                  kind=kind, evidence=value))
        ref = result.get('evidence_ref')
        if not isinstance(ref, str) or not _REF.fullmatch(ref):
            raise ValueError('Invalid Command Center evidence reference')
        return ref


def request_binding(data, now):
    """Bind a queued request to exact local input, clock and implementation bytes."""
    check_input(data)
    timestamp(now)
    validate('schemas/tenant.schema.json', data['tenant'])
    if (data.get('mode', 'shadow') != 'shadow'
            or data['brand'].get('status') != 'SYNTHETIC_SHADOW_PROFILE'
            or data['baseline'].get('source_type') != 'synthetic'
            or any(s.get('source_type') != 'synthetic' for s in data['sources'])
            or (data.get('analytics') and data['analytics'].get('source_type') != 'synthetic')):
        raise ValueError('Local integration accepts synthetic shadow data only')
    return dict(tenant_id=data['tenant']['tenant_id'], input_sha256=digest(data), at=now,
                source_sha256=runtime_provenance()['source_sha256'])


def _remote_run(response, run_id, worker_id, project_id, provider_id, status):
    value = response.get('run', {})
    if (not isinstance(value, dict) or value.get('id') != run_id
            or value.get('worker_id') != worker_id or value.get('project_id') != project_id
            or value.get('provider_id') != provider_id or value.get('status') != status):
        raise ValueError('Command Center run acknowledgement mismatch')
    return value


def shadow_once(*, client, run_id, project_id, provider_id, tenant_id, data, output_root, now):
    """Execute one explicitly selected queued fixture; never select or retry other work."""
    data = deepcopy(data)
    for identity in (run_id, project_id, provider_id, tenant_id):
        if not isinstance(identity, str) or not _ID.fullmatch(identity):
            raise ValueError('Invalid job identity')
    binding = request_binding(data, now)
    if binding['tenant_id'] != tenant_id:
        raise ValueError('Local tenant binding mismatch')
    pending = client.request('/api/execution/pending?'+urlencode({'worker_id':client.worker_id}))
    runs = pending.get('runs')
    if not isinstance(runs, list):
        raise ValueError('Invalid pending response')
    matches = [r for r in runs if isinstance(r, dict) and r.get('id') == run_id]
    if len(matches) != 1:
        raise ValueError('Selected run is not pending; reconcile acknowledged work separately')
    selected = matches[0]
    if (selected.get('worker_id') != client.worker_id or selected.get('project_id') != project_id
            or selected.get('provider_id') != provider_id or selected.get('action') != 'marketing.shadow.verify'
            or selected.get('status') != 'QUEUED' or selected.get('requires_owner_approval') is not False
            or selected.get('input') != binding):
        raise ValueError('Queued job does not match authorized local shadow request')
    receipt = client.evidence(run_id, 'receipt', dict(adapter='marketing-local-shadow-v1', **binding))
    checkpoint = client.evidence(run_id, 'checkpoint', dict(state='BEFORE_LOCAL_SHADOW', **binding))
    ack = client.request('/api/execution/acknowledge', dict(run_id=run_id, worker_id=client.worker_id,
                        receipt_ref=receipt, checkpoint_ref=checkpoint))
    _remote_run(ack, run_id, client.worker_id, project_id, provider_id, 'RUNNING')
    try:
        state = ack.get('state', {})
        projects = [p for p in state.get('projects', []) if p.get('id') == project_id]
        providers = [p for p in state.get('providers', []) if p.get('id') == provider_id]
        if (len(projects) != 1 or projects[0].get('desired_state') != 'RUNNING'
                or projects[0].get('assigned_worker_id') != client.worker_id
                or len(providers) != 1 or providers[0].get('enabled') is not True):
            raise ValueError('Project is not runnable at acknowledgement')
        client.request('/api/heartbeat', dict(worker_id=client.worker_id, current_project_id=project_id,
                                            state='RUNNING', progress=True))
        result = run(data, output_root, now)
        manifest = json.loads((Path(result['output_dir'])/'manifest.json').read_text(encoding='utf-8'))
        status = 'COMPLETE' if result['state'] == 'SHADOW_COMPLETE' else 'FAILED'
        summary = dict(shadow_run_id=result['run_id'], tenant_id=tenant_id, state=result['state'],
                       production_published=False, cost_usd=0, manifest_sha256=digest(manifest),
                       files=manifest['files'], **{'request_binding':binding})
    except Exception:
        failed = client.evidence(run_id, 'result', dict(state='LOCAL_SHADOW_FAILED', request_binding=binding))
        done = client.request('/api/execution/complete', dict(run_id=run_id, worker_id=client.worker_id,
                       status='FAILED', evidence_ref=failed, summary='Local shadow failed; local evidence preserved'))
        _remote_run(done, run_id, client.worker_id, project_id, provider_id, 'FAILED')
        client.request('/api/heartbeat', dict(worker_id=client.worker_id, current_project_id=project_id,
                                            state='FAILED', progress=True))
        raise ValueError('Local shadow failed; evidence preserved') from None
    evidence = client.evidence(run_id, 'result', summary)
    done = client.request('/api/execution/complete', dict(run_id=run_id, worker_id=client.worker_id,
                         status=status, evidence_ref=evidence, summary='Synthetic local shadow only; MC-017 remains gated'))
    _remote_run(done, run_id, client.worker_id, project_id, provider_id, status)
    client.request('/api/heartbeat', dict(worker_id=client.worker_id, current_project_id=project_id,
                                        state=status, progress=True))
    return result
