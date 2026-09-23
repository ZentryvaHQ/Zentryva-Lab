"""Tenant-scoped lifecycle for trusted, explicitly registered local modules.

This is not a security sandbox. Customer input never supplies Python import paths.
"""
from copy import deepcopy
import hashlib
import inspect
from pathlib import Path
import re
from jsonschema import Draft202012Validator, ValidationError, SchemaError
from .core import digest

_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
_VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')


class Registry:
    def __init__(self, tenant_id):
        if not isinstance(tenant_id, str) or not _ID.fullmatch(tenant_id):
            raise ValueError('Invalid module tenant')
        self.tenant_id = tenant_id
        self._entries = {}

    def _entry(self, module_id):
        if module_id not in self._entries:
            raise ValueError('Module not installed')
        return self._entries[module_id]

    def _prepare(self, manifest, handlers):
        required = {'module_id', 'version', 'core_api', 'dependencies', 'config_schema'}
        if not isinstance(manifest, dict) or set(manifest) != required:
            raise ValueError('Invalid module manifest')
        name = manifest['module_id']
        if not isinstance(name, str) or not _ID.fullmatch(name):
            raise ValueError('Invalid module identity')
        if not isinstance(manifest['version'], str) or not _VERSION.fullmatch(manifest['version']):
            raise ValueError('Exact module version required')
        if type(manifest['core_api']) is not int or manifest['core_api'] != 1:
            raise ValueError('Incompatible Core API')
        deps = manifest['dependencies']
        if (not isinstance(deps, list) or any(not isinstance(d,str) or not _ID.fullmatch(d) for d in deps)
                or name in deps or len(deps) != len(set(deps))):
            raise ValueError('Invalid module dependencies')
        schema = manifest['config_schema']
        if not isinstance(schema,dict) or schema.get('type') != 'object':
            raise ValueError('Object configuration schema required')
        # No schema reference resolution/network requests from plugin configuration.
        def has_reference(value):
            if isinstance(value,dict):
                return any(k in ('$ref','$dynamicRef') or has_reference(v) for k,v in value.items())
            return isinstance(value,list) and any(has_reference(v) for v in value)
        if has_reference(schema):
            raise ValueError('Configuration schema references are not supported')
        try:
            Draft202012Validator.check_schema(schema)
            digest(manifest)
        except (SchemaError, TypeError, ValueError):
            raise ValueError('Invalid configuration schema') from None
        if not isinstance(handlers,dict) or not handlers:
            raise ValueError('Module operations required')
        implementations = {}
        for operation, handler in handlers.items():
            if not isinstance(operation,str) or not _ID.fullmatch(operation) or not inspect.isfunction(handler):
                raise ValueError('Named Python function operation required')
            source = inspect.getsourcefile(handler)
            if source is None or not Path(source).is_file():
                raise ValueError('Inspectable module source required')
            implementations[operation] = dict(callable=handler.__qualname__,
                source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest())
        return dict(manifest=deepcopy(manifest), handlers=dict(handlers), implementations=implementations,
                    enabled=False, config={}, health='DISABLED')

    def install(self, manifest, handlers):
        entry = self._prepare(manifest, handlers)
        name = entry['manifest']['module_id']
        if name in self._entries:
            raise ValueError('Module already installed; use explicit replacement')
        self._entries[name] = entry

    def _check_dependants(self, module_id):
        if any(e['enabled'] and module_id in e['manifest']['dependencies'] for e in self._entries.values()):
            raise ValueError('Enabled module depends on this module')

    def enable(self, module_id, config):
        entry = self._entry(module_id)
        if entry['enabled']:
            raise ValueError('Disable module before reconfiguration')
        for dep in entry['manifest']['dependencies']:
            self._ready(dep)
        try:
            Draft202012Validator(entry['manifest']['config_schema']).validate(config)
            digest(config)
        except (ValidationError, TypeError, ValueError):
            raise ValueError('Module configuration rejected') from None
        entry.update(enabled=True, config=deepcopy(config), health='READY')

    def disable(self, module_id):
        entry = self._entry(module_id)
        self._check_dependants(module_id)
        entry.update(enabled=False, config={}, health='DISABLED')

    def remove(self, module_id):
        entry = self._entry(module_id)
        self._check_dependants(module_id)
        if entry['enabled']:
            raise ValueError('Disable module before removal')
        del self._entries[module_id]

    def replace(self, manifest, handlers):
        replacement = self._prepare(manifest, handlers)
        name = replacement['manifest']['module_id']
        entry = self._entry(name)
        self._check_dependants(name)
        if entry['enabled']:
            raise ValueError('Disable module before replacement')
        self._entries[name] = replacement

    def _ready(self, module_id, visited=None):
        visited = set() if visited is None else visited
        if module_id in visited:
            raise ValueError('Cyclic module dependencies')
        entry = self._entry(module_id)
        if not entry['enabled'] or entry['health'] != 'READY':
            raise ValueError('Module unavailable')
        for dependency in entry['manifest']['dependencies']:
            self._ready(dependency, visited | {module_id})

    def call(self, module_id, operation, *args):
        entry = self._entry(module_id)
        self._ready(module_id)
        if operation not in entry['handlers']:
            raise ValueError('Unknown module operation')
        try:
            return entry['handlers'][operation](self.tenant_id, deepcopy(entry['config']), *deepcopy(args))
        except Exception:
            entry['health'] = 'FAILED'
            raise ValueError('Module execution failed') from None

    def snapshot(self):
        return [dict(manifest=deepcopy(e['manifest']), implementations=deepcopy(e['implementations']),
                     enabled=e['enabled'], config_sha256=digest(e['config']), health=e['health'])
                for _,e in sorted(self._entries.items())]
