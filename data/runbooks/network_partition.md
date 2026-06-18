# Network Partition Runbook

## Symptoms
- Services cannot communicate across zones or nodes.
- Service mesh reports upstream connection failures.
- 503 responses increase.
- One availability zone shows abnormal error rate.

## Severity Guidance
- P1 when production traffic is broadly impacted.
- P2 when one zone or service group is impacted.
- P3 when internal traffic is degraded but customer impact is low.

## Immediate Checks
1. Check service mesh metrics.
2. Check node and zone health.
3. Check network policies.
4. Check recent firewall or routing changes.
5. Compare error rates by zone.

## Safe Remediation
1. Shift traffic away from impacted zone.
2. Restart unhealthy sidecar proxies.
3. Revert recent network policy changes.
4. Scale healthy zone replicas.
5. Notify platform and network owners.

## Long-Term Fix
- Add zone-level alerts.
- Add network policy validation.
- Add failover tests.
- Improve service mesh dashboards.
