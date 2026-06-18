# DNS Failure Runbook

## Symptoms
- Services report temporary failure in name resolution.
- External provider hostnames cannot be resolved.
- CoreDNS latency or error rate increases.
- Pods fail to connect to dependencies.

## Severity Guidance
- P1 when production payments, login, or checkout cannot reach dependencies.
- P2 when multiple services are degraded.
- P3 when isolated internal services are affected.

## Immediate Checks
1. Test DNS resolution from affected pods.
2. Check CoreDNS pod health.
3. Check CoreDNS logs for errors.
4. Check recent cluster DNS changes.
5. Verify external provider status.

## Safe Remediation
1. Restart unhealthy CoreDNS pods.
2. Scale CoreDNS replicas.
3. Clear local DNS cache where applicable.
4. Route traffic to secondary endpoint if configured.
5. Notify network owner for production DNS failure.

## Long-Term Fix
- Add DNS latency alerts.
- Add dependency fallback endpoints.
- Validate cluster DNS changes.
- Add synthetic DNS checks.
