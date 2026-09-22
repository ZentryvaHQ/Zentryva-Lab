import copy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]

def validator(path):
    schema = json.loads((ROOT / path).read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())

class Contracts(unittest.TestCase):
    def test_mc002_status_accepts_valid_and_rejects_invalid(self):
        v = validator('contracts/command-center-interface.schema.json')
        good = dict(work_id='MC-R1-SALEM-001', tenant_id='salem-botanicals',
                    component='research', state='TESTING', updated_at='2026-09-22T12:00:00Z', evidence_refs=[])
        v.validate(good)
        for field, value in [('state','PUBLISHED'), ('updated_at','yesterday'), ('cost_usd',-1), ('tenant_id','')]:
            with self.subTest(field=field):
                self.assertFalse(v.is_valid(dict(good, **{field:value})))

    def test_mc003_tenant_and_safety_boundaries(self):
        v = validator('schemas/tenant.schema.json')
        good = json.loads((ROOT / 'tenants/salem-botanicals.example.json').read_text())
        v.validate(good)
        for field in ['production_publish_requires_owner_approval','spending_requires_owner_approval','prohibit_sensitive_targeting']:
            bad = copy.deepcopy(good)
            bad['policies'][field] = False
            self.assertFalse(v.is_valid(bad))
        bad = copy.deepcopy(good)
        bad['objectives'] = []
        self.assertFalse(v.is_valid(bad))

    def test_mc004_identity_provenance(self):
        v = validator('schemas/marketing-record.schema.json')
        good = dict(tenant_id='salem-botanicals',record_id='r1',record_type='research',
                    objective='qualified leads',created_at='2026-09-22T12:00:00Z',
                    provenance=dict(source_type='synthetic',confidence=0.5))
        v.validate(good)
        for field in ['tenant_id','record_id','objective']:
            self.assertFalse(v.is_valid(dict(good, **{field:''})), field)
        bad=copy.deepcopy(good)
        bad['provenance']['confidence']=1.1
        self.assertFalse(v.is_valid(bad))
        self.assertFalse(v.is_valid(dict(good, created_at='invalid')))

if __name__ == '__main__':
    unittest.main()
