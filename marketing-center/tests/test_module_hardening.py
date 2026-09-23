import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_loop import inputs
from test_intelligence import NOW
from test_modules import spec, echo, crash
from mc.modules import Registry
from mc.catalog import configured_registry
from mc.workflow import run


class ModuleHardening(unittest.TestCase):
    def test_transitive_dependency_crash_blocks_descendant(self):
        registry=Registry('tenant-a')
        registry.install(spec('base'),{'echo':crash})
        registry.install(spec('middle',dependencies=['base']),{'echo':echo})
        registry.install(spec('leaf',dependencies=['middle']),{'echo':echo})
        for name in ('base','middle','leaf'):registry.enable(name,{})
        with self.assertRaises(ValueError):registry.call('base','echo','x')
        with self.assertRaises(ValueError):registry.call('leaf','echo','x')

    def test_null_selection_is_not_implicit_enablement(self):
        data=inputs();data['modules']=None
        with tempfile.TemporaryDirectory() as directory,self.assertRaises(ValueError):run(data,directory,NOW)

    def test_other_tenant_status_and_dashboard_do_not_claim_salem(self):
        data=inputs(); data['tenant']['tenant_id']='other-pilot'
        for field in ('brand','baseline','analytics'):data[field]['tenant_id']='other-pilot'
        data['brand']['name']='Other Pilot';data['brand']['approved_copy']='Explore Other Pilot information.'
        data['brand']['landing_url']='https://example.org/other'
        for source in data['sources']:source['tenant_id']='other-pilot'
        with tempfile.TemporaryDirectory() as directory:
            result=run(data,directory,NOW)
            self.assertNotIn('SALEM',result['status']['work_id'])
            page=(Path(result['output_dir'])/'dashboard.html').read_text(encoding='utf-8')
            self.assertNotIn('<title>Salem',page)

    def test_module_version_change_creates_new_run(self):
        with tempfile.TemporaryDirectory() as directory:
            before=run(inputs(),directory,NOW)
            registry=configured_registry(before['tenant_id'])
            for name in ('optimization','measurement','publishing','content','planning','intelligence'):
                registry.disable(name)
            from mc.catalog import research,competitors,strategy
            manifest=next(m['manifest'] for m in registry.snapshot() if m['manifest']['module_id']=='intelligence');manifest['version']='1.0.1'
            registry.replace(manifest,{'research':research,'competitors':competitors,'strategy':strategy})
            registry.enable('intelligence',{})
            for name in ('planning','content','publishing','measurement','optimization'):registry.enable(name,{})
            with patch('mc.workflow.configured_registry',return_value=registry):after=run(inputs(),directory,NOW)
            self.assertNotEqual(before['run_id'],after['run_id'])

    def test_replay_rejects_altered_module_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            result=run(inputs(),directory,NOW)
            path=Path(result['output_dir'])/'manifest.json'
            manifest=json.loads(path.read_text());manifest['runtime']['modules']=[]
            path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaises(ValueError):run(inputs(),directory,NOW)
