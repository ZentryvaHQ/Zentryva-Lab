import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from .workflow import run

def main():
    parser=argparse.ArgumentParser(description='Run a local Marketing Center shadow loop. No network calls, publishing or spend.')
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',default=Path('runs'),type=Path)
    parser.add_argument('--at',default=None,help='Fixed ISO timestamp for reproducible fixture replay')
    args=parser.parse_args()
    try:
        data=json.loads(args.input.read_text(encoding='utf-8'))
        result=run(data,args.output,args.at or datetime.now(timezone.utc).isoformat())
    except (ValueError,KeyError,TypeError,OSError,AttributeError):
        print('Shadow run rejected: invalid input or evidence/storage problem. No publication attempted. Check input fields and preserve existing evidence.',file=sys.stderr)
        return 2
    print(json.dumps({key:result[key] for key in ('run_id','state','output_dir','production_published','cost_usd')},indent=2))
    return 0

if __name__=='__main__':
    sys.exit(main())
