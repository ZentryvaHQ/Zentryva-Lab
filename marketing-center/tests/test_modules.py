import copy
import tempfile
import unittest
from test_loop import inputs
from test_intelligence import NOW
from mc import modules
from mc.workflow import run


def echo(tenant, config, value):
    config['label'] = config.get('label', '') + '!'
    return tenant + ':' + config['label'] + ':' + value


def crash(tenant, config, value):
    raise RuntimeError('private-provider-token')


def spec(name='example', **changes):
    result = dict(module_id=name, version='1.0.0', core_api=1, dependencies=[],
                  config_schema={'type':'object','properties':{'label':{'type':'string'}},'additionalProperties':False})
    result.update(changes)
    return result


class Modules(unittest.TestCase):
    def registry(self, tenant='tenant-a'):
        self.assertTrue(hasattr(modules, 'Registry'), 'P0 requires a module registry')
        return modules.Registry(tenant)

    def test_tenant_config_is_copied_and_disabled_calls_are_blocked(self):
        a=self.registry(); b=self.registry('tenant-b')
        for registry in (a,b): registry.install(spec(), {'echo':echo})
        config={'label':'A'}; a.enable('example',config); b.enable('example',{'label':'B'})
        config['label']='modified'
        self.assertEqual(a.call('example','echo','x'),'tenant-a:A!:x')
        self.assertEqual(a.call('example','echo','x'),'tenant-a:A!:x')
        self.assertEqual(b.call('example','echo','x'),'tenant-b:B!:x')
        a.disable('example')
        with self.assertRaises(ValueError):a.call('example','echo','x')
        self.assertEqual(b.call('example','echo','x'),'tenant-b:B!:x')
        a.remove('example');self.assertEqual(a.snapshot(),[])

    def test_incompatible_manifest_config_and_dependency_rejected(self):
        r=self.registry()
        for change in ({'core_api':2},{'version':'latest'},{'module_id':'../escape'},{'dependencies':['example']}):
            with self.subTest(change=change),self.assertRaises(ValueError):r.install(spec(**change),{'echo':echo})
        r.install(spec('dependent',dependencies=['example']),{'echo':echo})
        with self.assertRaises(ValueError):r.enable('dependent',{})
        r.install(spec(),{'echo':echo})
        with self.assertRaises(ValueError):r.enable('example',{'unknown':'secret'})
        r.enable('example',{});r.enable('dependent',{})
        for operation in (r.disable,r.remove):
            with self.assertRaises(ValueError):operation('example')
        with self.assertRaises(ValueError):r.replace(spec(version='1.1.0'),{'echo':echo})
        self.assertEqual(r.call('example','echo','x'),'tenant-a:!:x')

    def test_replacement_changes_version_and_requires_reenable(self):
        r=self.registry();r.install(spec(),{'echo':echo});r.enable('example',{})
        before=r.snapshot();r.disable('example')
        r.replace(spec(version='1.1.0'),{'echo':echo})
        with self.assertRaises(ValueError):r.call('example','echo','x')
        r.enable('example',{})
        self.assertNotEqual(before,r.snapshot())
        self.assertEqual(r.snapshot()[0]['manifest']['version'],'1.1.0')

    def test_module_crash_is_sanitized_and_health_fails(self):
        r=self.registry();r.install(spec(),{'echo':crash});r.enable('example',{})
        with self.assertRaisesRegex(ValueError,'Module execution failed') as error:r.call('example','echo','x')
        self.assertNotIn('private-provider-token',str(error.exception))
        self.assertEqual(r.snapshot()[0]['health'],'FAILED')
        with self.assertRaises(ValueError):r.call('example','echo','x')

    def test_workflow_explicit_disable_and_unknown_module_fail_without_output(self):
        from pathlib import Path
        for selection in ({},{'unknown':{}}):
            with self.subTest(selection=selection),tempfile.TemporaryDirectory() as directory:
                data=inputs();data['modules']=selection
                with self.assertRaises(ValueError):run(data,directory,NOW)
                self.assertEqual(list(Path(directory).iterdir()),[])

    def test_workflow_records_enabled_module_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            result=run(inputs(),directory,NOW)
            self.assertIn('modules',result['runtime'])
            self.assertEqual(result['runtime']['modules'][0]['manifest']['module_id'],'intelligence')
            self.assertEqual(result['state'],'SHADOW_COMPLETE')

if __name__=='__main__':unittest.main()
