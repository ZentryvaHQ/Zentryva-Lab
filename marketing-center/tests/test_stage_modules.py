import tempfile
import unittest
from test_loop import inputs
from test_intelligence import NOW
from mc.catalog import configured_registry
from mc.workflow import run

class StageModules(unittest.TestCase):
    def test_every_marketing_stage_has_lifecycle_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            result=run(inputs(),directory,NOW)
        names={m['manifest']['module_id'] for m in result['runtime']['modules']}
        self.assertEqual(names,{'intelligence','planning','content','publishing','measurement','optimization'})
        self.assertEqual(result['state'],'SHADOW_COMPLETE')

    def test_disabled_content_cannot_generate_assets(self):
        registry=configured_registry('salem-botanicals')
        names={m['manifest']['module_id'] for m in registry.snapshot()}
        self.assertIn('content',names)
        for name in ('optimization','measurement','publishing','content'):
            registry.disable(name)
        with self.assertRaises(ValueError):registry.call('content','create','irrelevant')

    def test_planning_rejects_foreign_strategy(self):
        registry=configured_registry('salem-botanicals')
        self.assertIn('planning',{m['manifest']['module_id'] for m in registry.snapshot()})
        with self.assertRaises(ValueError):
            registry.call('planning','campaign','increase qualified leads',dict(tenant_id='foreign'),NOW)

if __name__=='__main__':unittest.main()
