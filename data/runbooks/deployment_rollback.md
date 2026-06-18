# Deployment Rollback Runbook

## Symptoms
- Error rate increases immediately after deployment.
- New version shows exceptions not seen before.
- Health checks fail after release.
- Customer-facing APIs fail after code change.

## Severity Guidance
- P1 when production critical flows fail.
- P2 when major but recoverable degradation occurs.
- P3 when non-critical service behavior is affected.
- P4 when staging or development only is affected.

## Immediate Checks
1. Confirm deployment timestamp.
2. Compare error rate before and after deployment.
3. Check application logs for new exceptions.
4. Verify current image version.
5. Check rollout status.

## Safe Remediation
1. Roll back to the previous stable version.
2. Restart affected deployment.
3. Disable faulty feature flag.
4. Verify service health after rollback.
5. Notify service owner and on-call engineer.

## Long-Term Fix
- Add canary deployment.
- Add automated rollback checks.
- Add regression tests.
- Add feature flag safeguards.
