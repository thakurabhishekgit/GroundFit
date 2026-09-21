# Gmail API email on Render free (no custom domain)

Emails send **From: GroundFit \<groundfit.in@gmail.com\>** via Gmail’s HTTPS API
(port 443). Works on Render free (SMTP ports are blocked).

## One-time Google Cloud setup

1. [Google Cloud Console](https://console.cloud.google.com/) → your GroundFit project  
2. **APIs & Services → Enable APIs** → enable **Gmail API**  
3. **OAuth consent screen**  
   - External (or Internal if Workspace)  
   - Add scope: `https://www.googleapis.com/auth/gmail.send`  
   - **Test users** → add `groundfit.in@gmail.com`  
4. **Credentials → Create credentials → OAuth client ID**  
   - Application type: **Desktop app** (easiest for the setup script)  
   - Copy Client ID + Client Secret  

> You can reuse the existing Web client ID/secret if it allows the desktop/local
> redirect; if the script fails, create a dedicated **Desktop** OAuth client.

## Get the refresh token (run once on your PC)

```bash
cd GroundFit
.\apps\api\.venv\Scripts\pip install google-auth-oauthlib
# put GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET in .env (or GOOGLE_*)
.\apps\api\.venv\Scripts\python scripts\gmail_oauth_setup.py
```

Browser opens → sign in as **groundfit.in@gmail.com** → Allow.  
Copy the printed `GMAIL_REFRESH_TOKEN=...`

## Env (local `.env` + Render)

```
EMAIL_ENABLED=true
EMAIL_PROVIDER=gmail
GMAIL_SENDER=groundfit.in@gmail.com
SMTP_FROM=GroundFit <groundfit.in@gmail.com>
GMAIL_OAUTH_CLIENT_ID=....apps.googleusercontent.com
GMAIL_OAUTH_CLIENT_SECRET=....
GMAIL_REFRESH_TOKEN=1//....
```

Redeploy Render. Test: `POST /api/v1/lists/email/test` while logged in.

Recipients = each user’s **Google login email**. Sender = `groundfit.in@gmail.com`.
