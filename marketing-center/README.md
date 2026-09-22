# Zentryva AI Marketing Center — R1 Salem Sprint

Status: ACTIVE DEVELOPMENT
Work ID: MC-R1-SALEM-001
Branch: mc-r1-salem-sprint

## R1 completion target
Deliver one usable end-to-end Salem Botanicals marketing loop:
objective -> evidence-backed research -> opportunity -> strategy -> campaign -> content -> brand/compliance gates -> publishing handoff -> delivery evidence -> analytics -> attribution -> learning -> next recommendation.

## Architecture boundary
Command Center manages shared scheduling, jobs, health, retries, blockers, evidence, execution history, cost monitoring, permissions and shared corporate memory interfaces.
Marketing Center owns marketing intelligence and decisions.
No permanent duplicate infrastructure is allowed here.

## Sprint constraints
- Safe, reversible, non-production work only.
- No secrets in Git.
- No paid spend.
- No production publishing without owner approval.
- Tenant-aware from the first schema.
- Commercial SaaS shell deferred until R1 works.
- Human review is permitted in R1 to accelerate the pilot.
