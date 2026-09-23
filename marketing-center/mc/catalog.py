"""Trusted bundled module catalog. No imports are selected by customer data."""
from . import intelligence, stages
from .modules import Registry


def research(tenant, config, objective, sources, now):
    return intelligence.research(tenant, objective, sources, now)


def competitors(tenant, config, objective, evidence, now):
    return intelligence.competitors(tenant, objective, evidence, now)


def strategy(tenant, config, objective, evidence, rivals, now):
    return intelligence.strategy(tenant, objective, evidence, rivals, now)

def campaign(tenant, config, *args): return stages.plan_campaign(tenant,*args)
def create(tenant, config, *args): return stages.create_content(tenant,*args)
def review(tenant, config, *args): return stages.review(tenant,*args)
def handoff(tenant, config, *args): return stages.handoff(tenant,*args)
def delivery(tenant, config, *args): return stages.delivery(tenant,*args)
def normalize(tenant, config, *args): return stages.normalize(tenant,*args)
def attribute(tenant, config, *args): return stages.attribute(tenant,*args)
def learn(tenant, config, *args): return stages.learn(tenant,*args)
def optimize(tenant, config, *args): return stages.optimize(tenant,*args)


def configured_registry(tenant, selection=None):
    registry = Registry(tenant)
    registry.install(dict(module_id='intelligence', version='1.0.0', core_api=1, dependencies=[],
        config_schema={'type':'object','maxProperties':0}),
        {'research':research,'competitors':competitors,'strategy':strategy})
    bundled=[('planning',['intelligence'],{'campaign':campaign}),
             ('content',['planning'],{'create':create,'review':review}),
             ('publishing',['content'],{'handoff':handoff,'delivery':delivery}),
             ('measurement',['publishing'],{'normalize':normalize,'attribute':attribute}),
             ('optimization',['measurement'],{'learn':learn,'next':optimize})]
    for name,deps,handlers in bundled:
        registry.install(dict(module_id=name,version='1.0.0',core_api=1,dependencies=deps,
            config_schema={'type':'object','maxProperties':0}),handlers)
    if selection is None:
        selection = {'intelligence':{}}
    required={'intelligence'}|{name for name,_,_ in bundled}
    if not isinstance(selection,dict) or set(selection) not in ({'intelligence'},required):
        raise ValueError('Shadow workflow requires all bundled stages')
    # Preserve the previously documented intelligence-only configuration shorthand.
    configs={name:{} for name in required};configs.update(selection)
    for name in ['intelligence']+[name for name,_,_ in bundled]:
        registry.enable(name,configs[name])
    return registry
