# Rate Limit Incident Runbook

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
