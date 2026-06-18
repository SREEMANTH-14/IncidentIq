# Database Connection Pool Exhaustion Runbook

## Symptoms
- SQLTimeoutException or connection acquisition timeout.
- Database pool usage above 90 percent.
- Increased API latency and failed checkout or payment requests.
- Application threads waiting for database connections.

## Severity Guidance
- P1 when customer transactions fail in production.
- P2 when latency is high but partial traffic still succeeds.
- P3 when the issue is isolated to non-critical workloads.

## Immediate Checks
1. Check active database connections.
2. Check connection pool usage by service.
3. Review slow query dashboard.
4. Confirm whether a recent deployment changed connection handling.
5. Check for connection leaks in logs.

## Safe Remediation
1. Restart the affected service only if connection leak symptoms are confirmed.
2. Temporarily scale service replicas if traffic is high.
3. Increase connection pool size only within database capacity limits.
4. Reduce non-critical background jobs.
5. Notify on-call database owner for P1 and P2 incidents.

## Long-Term Fix
- Add connection leak detection.
- Tune pool max size and timeout.
- Add slow query indexes.
- Add alerts for pool usage above 85 percent.
