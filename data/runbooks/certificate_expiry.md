# Certificate Expiry Runbook

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
