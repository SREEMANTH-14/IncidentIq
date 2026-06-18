# Slow Database Query Runbook

## Symptoms
- API latency increases.
- Database CPU increases.
- Query dashboard shows slow queries.
- Sequential scans or missing indexes appear in query plans.

## Severity Guidance
- P1 when critical transaction APIs fail.
- P2 when major APIs are slow.
- P3 when dashboards or reports are delayed.

## Immediate Checks
1. Identify top slow queries.
2. Review query execution plans.
3. Check missing indexes.
4. Check recent schema or query changes.
5. Check database locks.

## Safe Remediation
1. Disable expensive non-critical reports.
2. Add temporary query timeout for bad paths.
3. Scale read replicas if supported.
4. Roll back query change if recently deployed.
5. Notify database owner.

## Long-Term Fix
- Add missing indexes.
- Optimize query filters.
- Add query performance tests.
- Add slow query alerts.
