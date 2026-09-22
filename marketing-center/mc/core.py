import hashlib
import json
import math
import platform
import subprocess
from importlib.metadata import version
from datetime import datetime
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]

def runtime_provenance():
    paths = sorted(list((ROOT/'mc').glob('*.py')) + list((ROOT/'schemas').glob('*.json'))
                   + list((ROOT/'contracts').glob('*.json')) + [ROOT/'requirements.txt'])
    source_hash = digest({str(p.relative_to(ROOT)).replace('\\','/'):p.read_text(encoding='utf-8') for p in paths})
    try:
        commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
    except (OSError,subprocess.CalledProcessError):
        commit = None
    return dict(source_sha256=source_hash,git_commit=commit,python=platform.python_version(),jsonschema=version('jsonschema'))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError('timezone required')
        return result
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Invalid timestamp') from exc

def validate(path, value):
    schema = json.loads((ROOT / path).read_text(encoding='utf-8'))
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    except ValidationError as exc:
        # Do not echo untrusted payloads (which might contain credentials).
        raise ValueError('Schema validation failed at ' + '.'.join(map(str, exc.path))) from None

def scoped(tenant, records, objective=None):
    for record in records:
        if record.get('tenant_id') != tenant:
            raise ValueError('Cross-tenant input rejected')
        if objective is not None and record.get('objective') != objective:
            raise ValueError('Objective mismatch')

def number(value, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Finite number required')
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError('Number outside permitted bounds')
    return value

def record(tenant, kind, objective, now, refs=(), **payload):
    timestamp(now)
    item = dict(tenant_id=tenant, record_type=kind, objective=objective, created_at=now,
                provenance=dict(source_type='derived-shadow', confidence=payload.pop('confidence', 0.5)),
                evidence_refs=list(refs), **payload)
    item['record_id'] = kind + '-' + digest(item)[:20]
    validate('schemas/marketing-record.schema.json', item)
    return item
