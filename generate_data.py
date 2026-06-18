import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("IncidentIQ.GenerateData")


def get_synthetic_incidents() -> list[dict[str, Any]]:
    """
    Creates 25 realistic historical production incidents.

    These incidents follow the structure required by the IncidentIQ use case:
    - id
    - title
    - description
    - severity
    - category
    - resolution
    - resolved_at

    The data covers common DevOps/SRE scenarios such as:
    database connection pools, OOMKilled pods, disk full, Redis CPU,
    DNS failures, certificate expiry, slow queries, rate limits,
    deployment rollbacks, and network partitions.
    """

    incidents: list[dict[str, Any]] = [
        {
            "id": "INC-001",
            "title": "Database connection pool exhausted",
            "description": (
                "Checkout service started failing with SQLTimeoutException. "
                "Database pool usage reached 98 percent and API latency crossed 2400 ms. "
                "The incident impacted payment and order placement flows."
            ),
            "severity": "P1",
            "category": "database",
            "resolution": (
                "Increased database connection pool size temporarily, restarted checkout-service, "
                "and fixed a connection leak in the payment repository layer."
            ),
            "resolved_at": "2025-01-08T10:45:00Z",
        },
        {
            "id": "INC-002",
            "title": "OOMKilled pods in recommendation service",
            "description": (
                "Recommendation service pods were repeatedly restarted with OOMKilled status. "
                "Memory usage increased after a new model cache was enabled. "
                "Users saw partial product recommendation failures."
            ),
            "severity": "P2",
            "category": "infra",
            "resolution": (
                "Increased pod memory limits, reduced model cache size, and added memory alerts "
                "for container working set usage."
            ),
            "resolved_at": "2025-01-17T14:30:00Z",
        },
        {
            "id": "INC-003",
            "title": "Application disk full on logging node",
            "description": (
                "Log ingestion node stopped accepting new log batches because disk usage reached 100 percent. "
                "Fluent Bit showed write failures and backlog increased quickly."
            ),
            "severity": "P2",
            "category": "infra",
            "resolution": (
                "Rotated old logs, expanded the persistent volume, and added retention rules "
                "for debug-level logs."
            ),
            "resolved_at": "2025-01-26T08:15:00Z",
        },
        {
            "id": "INC-004",
            "title": "Redis high CPU causing session latency",
            "description": (
                "Redis primary CPU stayed above 95 percent for 20 minutes. "
                "Session lookup latency increased and login requests intermittently timed out."
            ),
            "severity": "P2",
            "category": "database",
            "resolution": (
                "Moved hot keys to a sharded cache pattern, reduced expensive key scans, "
                "and restarted the overloaded Redis node during the maintenance window."
            ),
            "resolved_at": "2025-02-03T19:20:00Z",
        },
        {
            "id": "INC-005",
            "title": "DNS resolution failure for payment provider",
            "description": (
                "Payment service could not resolve the external provider hostname. "
                "Pods reported temporary failure in name resolution and payment authorization failed."
            ),
            "severity": "P1",
            "category": "network",
            "resolution": (
                "Restarted CoreDNS pods, cleared stale DNS cache, and switched payment provider calls "
                "to the secondary endpoint until DNS stabilized."
            ),
            "resolved_at": "2025-02-10T11:05:00Z",
        },
        {
            "id": "INC-006",
            "title": "TLS certificate expired for public API gateway",
            "description": (
                "Public API gateway returned TLS handshake errors after the edge certificate expired. "
                "External clients were unable to connect to production APIs."
            ),
            "severity": "P1",
            "category": "network",
            "resolution": (
                "Renewed and deployed the TLS certificate, reloaded gateway configuration, "
                "and added certificate expiry monitoring at 30, 14, and 7 days."
            ),
            "resolved_at": "2025-02-21T05:40:00Z",
        },
        {
            "id": "INC-007",
            "title": "Slow product search queries",
            "description": (
                "Product search API latency increased to 3200 ms. "
                "Database monitoring showed sequential scans on the product_catalog table."
            ),
            "severity": "P2",
            "category": "database",
            "resolution": (
                "Added missing index on category_id and updated query filters to reduce full table scans."
            ),
            "resolved_at": "2025-03-01T16:25:00Z",
        },
        {
            "id": "INC-008",
            "title": "Rate limit errors from notification provider",
            "description": (
                "Notification service received HTTP 429 responses from the SMS provider. "
                "Retry storms increased queue depth and delayed OTP delivery."
            ),
            "severity": "P2",
            "category": "application",
            "resolution": (
                "Added exponential backoff, reduced retry concurrency, and routed priority OTP traffic "
                "through the backup notification provider."
            ),
            "resolved_at": "2025-03-09T13:10:00Z",
        },
        {
            "id": "INC-009",
            "title": "Bad deployment caused checkout failures",
            "description": (
                "A new checkout-service release introduced a null pointer error in the discount calculation path. "
                "Error rate crossed 18 percent after deployment."
            ),
            "severity": "P1",
            "category": "application",
            "resolution": (
                "Rolled back checkout-service to the previous stable release and added regression tests "
                "for discount validation."
            ),
            "resolved_at": "2025-03-14T09:55:00Z",
        },
        {
            "id": "INC-010",
            "title": "Network partition between service mesh nodes",
            "description": (
                "Several pods reported upstream connection failures across two availability zones. "
                "Service mesh telemetry showed increased 503 responses."
            ),
            "severity": "P1",
            "category": "network",
            "resolution": (
                "Shifted traffic away from the impacted zone, restarted affected sidecar proxies, "
                "and validated network policy changes."
            ),
            "resolved_at": "2025-03-28T22:35:00Z",
        },
        {
            "id": "INC-011",
            "title": "CPU throttling in order service",
            "description": (
                "Order service latency increased during peak traffic. "
                "Kubernetes metrics showed CPU throttling above 70 percent."
            ),
            "severity": "P3",
            "category": "infra",
            "resolution": (
                "Increased CPU limits, tuned autoscaling thresholds, and enabled dashboard alerts "
                "for throttling."
            ),
            "resolved_at": "2025-04-04T12:00:00Z",
        },
        {
            "id": "INC-012",
            "title": "Kafka consumer lag in billing pipeline",
            "description": (
                "Billing events were delayed because consumer lag crossed 250000 messages. "
                "A slow downstream database write path blocked consumer throughput."
            ),
            "severity": "P2",
            "category": "application",
            "resolution": (
                "Scaled consumer replicas, optimized batch writes, and temporarily paused non-critical topics."
            ),
            "resolved_at": "2025-04-12T18:45:00Z",
        },
        {
            "id": "INC-013",
            "title": "Staging deployment failed health checks",
            "description": (
                "Staging deployment did not pass readiness checks after configuration changes. "
                "The service was not receiving production traffic."
            ),
            "severity": "P4",
            "category": "application",
            "resolution": (
                "Corrected the staging environment variable and redeployed the service."
            ),
            "resolved_at": "2025-04-20T07:30:00Z",
        },
        {
            "id": "INC-014",
            "title": "Image pull backoff in worker namespace",
            "description": (
                "Background worker pods failed with ImagePullBackOff after a registry token rotation. "
                "Scheduled jobs were delayed but customer-facing APIs were healthy."
            ),
            "severity": "P3",
            "category": "infra",
            "resolution": (
                "Updated image pull secret, restarted worker deployment, and verified registry access."
            ),
            "resolved_at": "2025-05-02T06:50:00Z",
        },
        {
            "id": "INC-015",
            "title": "API gateway 503 errors after config reload",
            "description": (
                "API gateway returned intermittent 503 responses after a routing configuration reload. "
                "The issue affected a subset of mobile clients."
            ),
            "severity": "P2",
            "category": "network",
            "resolution": (
                "Reverted gateway route configuration, warmed upstream connection pools, "
                "and added validation checks before reload."
            ),
            "resolved_at": "2025-05-09T15:15:00Z",
        },
        {
            "id": "INC-016",
            "title": "Elasticsearch indexing delay",
            "description": (
                "Search indexing delay increased to 45 minutes after bulk import jobs started. "
                "Users saw stale product search results."
            ),
            "severity": "P3",
            "category": "database",
            "resolution": (
                "Paused the bulk import job, increased indexing workers, and tuned refresh interval."
            ),
            "resolved_at": "2025-05-16T20:05:00Z",
        },
        {
            "id": "INC-017",
            "title": "Memory leak in inventory service",
            "description": (
                "Inventory service memory usage increased gradually after the latest release. "
                "Pods restarted every 40 minutes and inventory updates were delayed."
            ),
            "severity": "P2",
            "category": "application",
            "resolution": (
                "Rolled back the release, identified an unclosed HTTP client, and patched the leak."
            ),
            "resolved_at": "2025-05-24T11:40:00Z",
        },
        {
            "id": "INC-018",
            "title": "Database replica lag crossed threshold",
            "description": (
                "Read replica lag crossed 600 seconds during reporting workload execution. "
                "Analytics dashboards showed delayed data."
            ),
            "severity": "P3",
            "category": "database",
            "resolution": (
                "Moved reporting workload to a separate replica and reduced long-running analytical queries."
            ),
            "resolved_at": "2025-06-02T10:10:00Z",
        },
        {
            "id": "INC-019",
            "title": "Ingress controller pod crash loop",
            "description": (
                "Ingress controller entered CrashLoopBackOff after a malformed annotation was deployed. "
                "Some internal services became unreachable."
            ),
            "severity": "P2",
            "category": "infra",
            "resolution": (
                "Removed malformed ingress annotation, restarted ingress controller, and added manifest validation."
            ),
            "resolved_at": "2025-06-11T17:25:00Z",
        },
        {
            "id": "INC-020",
            "title": "Object storage timeout during invoice generation",
            "description": (
                "Invoice generation service timed out while writing PDF files to object storage. "
                "The provider status page showed elevated latency in one region."
            ),
            "severity": "P3",
            "category": "network",
            "resolution": (
                "Switched writes to secondary object storage region and retried failed invoice jobs."
            ),
            "resolved_at": "2025-06-19T09:35:00Z",
        },
        {
            "id": "INC-021",
            "title": "Minor CPU increase in reporting service",
            "description": (
                "Reporting service CPU increased to 72 percent for 10 minutes. "
                "No customer impact was observed and latency stayed within SLO."
            ),
            "severity": "P4",
            "category": "application",
            "resolution": (
                "Observed the service, confirmed no SLO breach, and kept the alert as informational."
            ),
            "resolved_at": "2025-07-01T04:20:00Z",
        },
        {
            "id": "INC-022",
            "title": "Checkout API error budget burn",
            "description": (
                "Checkout API started burning error budget faster than expected. "
                "Error rate stayed at 4 percent after a traffic spike."
            ),
            "severity": "P2",
            "category": "application",
            "resolution": (
                "Scaled checkout-service replicas, enabled request shedding for low-priority traffic, "
                "and reviewed dependency latency."
            ),
            "resolved_at": "2025-07-09T21:10:00Z",
        },
        {
            "id": "INC-023",
            "title": "CoreDNS latency after cluster upgrade",
            "description": (
                "DNS lookup latency increased after a Kubernetes cluster upgrade. "
                "Several services reported delayed dependency connections."
            ),
            "severity": "P2",
            "category": "network",
            "resolution": (
                "Increased CoreDNS replicas, reviewed cluster DNS config, and restarted affected deployments."
            ),
            "resolved_at": "2025-07-18T12:55:00Z",
        },
        {
            "id": "INC-024",
            "title": "Pod pending due to insufficient memory",
            "description": (
                "New analytics pods stayed in Pending state because the cluster had insufficient memory. "
                "Batch processing was delayed but APIs were unaffected."
            ),
            "severity": "P3",
            "category": "infra",
            "resolution": (
                "Scaled the node group, reduced analytics pod requests, and added capacity alerts."
            ),
            "resolved_at": "2025-07-27T23:05:00Z",
        },
        {
            "id": "INC-025",
            "title": "Payment webhook signature validation failure",
            "description": (
                "Payment webhook processor rejected valid callbacks after a secret rotation mismatch. "
                "Order status updates were delayed for successful payments."
            ),
            "severity": "P1",
            "category": "application",
            "resolution": (
                "Rolled back the webhook secret, replayed missed callbacks, and added secret rotation validation."
            ),
            "resolved_at": "2025-08-04T06:25:00Z",
        },
    ]

    return incidents


def get_synthetic_runbooks() -> dict[str, str]:
    """
    Creates markdown runbooks for IncidentIQ RAG retrieval.

    These runbooks are intentionally concise and operational.
    The Knowledge Agent will retrieve chunks from these files later.
    """

    runbooks: dict[str, str] = {
        "database_connection_pool.md": """# Database Connection Pool Exhaustion Runbook

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
""",
        "oomkilled_pods.md": """# OOMKilled Pods Runbook

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
""",
        "disk_full.md": """# Disk Full Runbook

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
""",
        "redis_high_cpu.md": """# Redis High CPU Runbook

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
""",
        "dns_failure.md": """# DNS Failure Runbook

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
""",
        "certificate_expiry.md": """# Certificate Expiry Runbook

## Symptoms
- TLS handshake failures.
- Browser or API clients report expired certificate.
- Public API gateway rejects secure connections.
- Monitoring shows certificate expiry date in the past.

## Severity Guidance
- P1 when public production traffic cannot connect.
- P2 when a subset of clients or internal services are affected.
- P3 when expiry is upcoming but not active.

## Immediate Checks
1. Check certificate expiry date.
2. Check gateway or ingress certificate secret.
3. Confirm certificate chain validity.
4. Review recent certificate rotation jobs.
5. Test endpoint with TLS validation.

## Safe Remediation
1. Renew certificate.
2. Update Kubernetes TLS secret.
3. Reload ingress or gateway.
4. Verify endpoint after deployment.
5. Notify security and platform owners.

## Long-Term Fix
- Add expiry alerts at 30, 14, and 7 days.
- Automate certificate renewal.
- Add certificate validation in deployment pipeline.
""",
        "slow_queries.md": """# Slow Database Query Runbook

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
""",
        "rate_limits.md": """# Rate Limit Incident Runbook

## Symptoms
- External provider returns HTTP 429.
- Retry queue depth increases.
- OTP, email, SMS, or webhook delivery is delayed.
- Application logs show too many requests.

## Severity Guidance
- P1 when authentication or payment verification is unavailable.
- P2 when user communication is delayed.
- P3 when non-critical notifications are delayed.

## Immediate Checks
1. Check provider rate limit dashboard.
2. Check retry volume.
3. Check queue depth.
4. Identify noisy clients or jobs.
5. Confirm backup provider availability.

## Safe Remediation
1. Enable exponential backoff.
2. Reduce retry concurrency.
3. Pause non-critical notifications.
4. Route priority traffic to backup provider.
5. Notify vendor owner.

## Long-Term Fix
- Add adaptive throttling.
- Add dead-letter queue.
- Add provider quota alerts.
- Separate priority and non-priority traffic.
""",
        "deployment_rollback.md": """# Deployment Rollback Runbook

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
""",
        "network_partition.md": """# Network Partition Runbook

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
""",
    }

    return runbooks


def write_json_file(file_path: Path, data: list[dict[str, Any]]) -> None:
    """
    Writes incident data to a JSON file.

    The parent directory is created automatically if it does not exist.
    """

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    logger.info("Incident data written to %s", file_path)


def write_markdown_files(directory_path: Path, runbooks: dict[str, str]) -> None:
    """
    Writes each runbook as a separate markdown file.
    """

    directory_path.mkdir(parents=True, exist_ok=True)

    for file_name, content in runbooks.items():
        file_path = directory_path / file_name

        with file_path.open("w", encoding="utf-8") as file:
            file.write(content.strip())
            file.write("\n")

        logger.info("Runbook written to %s", file_path)


def generate_synthetic_data() -> None:
    """
    Main data generation function for IncidentIQ.

    It creates:
    - data/incidents/incidents.json
    - data/runbooks/*.md
    """

    settings = get_settings()
    settings.create_required_directories()

    incidents = get_synthetic_incidents()
    runbooks = get_synthetic_runbooks()

    incident_data_file_path = settings.get_incident_data_file_path()
    runbook_data_directory = settings.get_runbook_data_directory()

    write_json_file(incident_data_file_path, incidents)
    write_markdown_files(runbook_data_directory, runbooks)

    logger.info("Synthetic data generation completed successfully.")
    logger.info("Total incidents generated: %s", len(incidents))
    logger.info("Total runbooks generated: %s", len(runbooks))


if __name__ == "__main__":
    generate_synthetic_data()
