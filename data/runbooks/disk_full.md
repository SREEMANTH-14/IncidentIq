# Disk Full Runbook

## Symptoms
- Disk usage reaches 95 to 100 percent.
- Applications fail to write logs, files, or temporary data.
- Log shippers report write failures.
- Databases may reject writes when volume is full.

## Severity Guidance
- P1 when writes fail for customer-facing systems.
- P2 when log ingestion or internal pipelines are blocked.
- P3 when cleanup is required but service is still healthy.

## Immediate Checks
1. Check disk usage by mount path.
2. Find largest directories.
3. Check log retention policy.
4. Check whether debug logs increased.
5. Confirm persistent volume capacity.

## Safe Remediation
1. Delete safe temporary files.
2. Rotate old logs.
3. Expand persistent volume if supported.
4. Restart log shipper after cleanup.
5. Notify infrastructure owner for repeated disk alerts.

## Long-Term Fix
- Add retention policy.
- Add disk usage alerts.
- Move large artifacts to object storage.
- Reduce verbose logging in production.
