"""Trusted bundled module catalog. No imports are selected by customer data."""
from . import intelligence
from .modules import Registry


def research(tenant, config, objective, sources, now):
    return intelligence.research(tenant, objective, sources, now)


def competitors(tenant, config, objective, evidence, now):
    return intelligence.competitors(tenant, objective, evidence, now)


def strategy(tenant, config, objective, evidence, rivals, now):
    return intelligence.strategy(tenant, objective, evidence, rivals, now)


def configured_registry(tenant, selection=None):
    registry = Registry(tenant)
    registry.install(dict(module_id='intelligence', version='1.0.0', core_api=1, dependencies=[],
        config_schema={'type':'object','maxProperties':0}),
        {'research':research,'competitors':competitors,'strategy':strategy})
    if selection is None:
        selection = {'intelligence':{}}
    if not isinstance(selection,dict) or set(selection) != {'intelligence'}:
        raise ValueError('Shadow workflow requires the intelligence module')
    for name, config in selection.items():
        registry.enable(name, config)
    return registry
