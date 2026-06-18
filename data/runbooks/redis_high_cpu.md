# Redis High CPU Runbook

## Symptoms
- Redis CPU usage above 90 percent.
- Session or cache lookups become slow.
- Login, cart, or personalization flows show latency.
- Redis slow log contains expensive commands.

## Severity Guidance
- P1 when login or checkout is unavailable.
- P2 when latency affects major user flows.
- P3 when only background cache updates are delayed.

## Immediate Checks
1. Check Redis CPU and memory.
2. Review Redis slow log.
3. Identify hot keys.
4. Check command stats for KEYS or large scans.
5. Confirm client retry behavior.

## Safe Remediation
1. Reduce expensive scans.
2. Shift read traffic to replicas if available.
3. Restart non-critical consumers causing load.
4. Apply rate limits to noisy clients.
5. Notify cache owner for P1 and P2 incidents.

## Long-Term Fix
- Replace KEYS with SCAN.
- Add sharding for hot keys.
- Add TTL policies.
- Add Redis CPU alerts.
