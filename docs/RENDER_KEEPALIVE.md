# Render free tier + keep-alive + email (GroundFit API)

## Why production emails failed

Your Render logs show the reminder poll finding due jobs, then ~30s delay and
**no successful send**. That matches **Render free blocking outbound SMTP**
(ports `25`, `465`, `587`) as of Sep 2025.

- Local Gmail SMTP works
- Render free → connection timeout / unreachable → no inbox mail

**Fix:** use **Resend** (HTTPS API, port 443) on Render.

### Resend setup

1. https://resend.com → create API key  
2. Render env:

```
EMAIL_ENABLED=true
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxx
RESEND_FROM=GroundFit <onboarding@resend.dev>
```

3. Redeploy API  
4. Logged in: `GET /api/v1/lists/email/status` and `POST /api/v1/lists/email/test`

Notes:

- `onboarding@resend.dev` is for testing; often only delivers to your Resend account email.
- To email **any** Google login user, verify a domain in Resend and set `RESEND_FROM` to that domain.
- Paid Render can use Gmail SMTP again; free cannot.

## Idle spin-down

| Event | Timing |
|--------|--------|
| Sleep | ~**15 min** with no inbound HTTP |
| Wake | Next HTTP request |
| Cold start | ~**1 min** |

Scheduler: every **10 minutes** (`*/10 * * * *`). See `.github/workflows/keepalive-reminders.yml`.
