# OOMKilled Pods Runbook

## Symptoms
- Kubernetes pod status shows OOMKilled.
- Container restarts increase repeatedly.
- Memory usage grows until the container is killed.
- Application logs may stop abruptly before restart.

## Severity Guidance
- P1 when critical production APIs are unavailable.
- P2 when repeated restarts impact customer-facing traffic.
- P3 when background jobs are delayed.
- P4 when the issue is isolated to staging or development.

## Immediate Checks
1. Check pod restart count.
2. Check container memory usage.
3. Compare memory request and limit.
4. Review recent deployments.
5. Check for memory leak patterns.

## Safe Remediation
1. Scale replicas if enough cluster capacity exists.
2. Increase memory limit temporarily.
3. Restart unhealthy pods.
4. Roll back recent deployment when memory leak started after release.
5. Notify service owner for production impact.

## Long-Term Fix
- Add memory profiling.
- Tune JVM or runtime memory settings.
- Reduce cache size.
- Add alerts for memory working set usage.
