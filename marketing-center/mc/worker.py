"""Explicit one-shot local Command Center worker entry point."""
import argparse
import json
import os
from pathlib import Path
from .command_center import LocalCommandCenter, shadow_once
from .supervised import shadow_supervised


def main():
    parser = argparse.ArgumentParser(description='Run one explicitly queued synthetic shadow job on local Command Center')
    for name in ('url', 'worker-id', 'run-id', 'project-id', 'provider-id', 'tenant-id', 'at'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--supervised', action='store_true', help='Use shared cooperative-v1 pause/recovery protocol')
    args = parser.parse_args()
    try:
        client = LocalCommandCenter(args.url, args.worker_id, os.environ.get('MC_CC_WORKER_TOKEN'))
        data = json.loads(args.input.read_text(encoding='utf-8'))
        execute = shadow_supervised if args.supervised else shadow_once
        result = execute(client=client, run_id=args.run_id, project_id=args.project_id,
            provider_id=args.provider_id, tenant_id=args.tenant_id, data=data,
            output_root=args.output, now=args.at)
        print(json.dumps(dict(state=result['state'], run_id=result['run_id'],
                              production_published=False, cost_usd=0)))
        return 0 if result['state'] == 'SHADOW_COMPLETE' else (3 if result['state']=='SUSPENDED' else 1)
    except Exception:
        print(json.dumps(dict(state='ADAPTER_FAILED', message='Preserve evidence and reconcile shared run state before retry')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
