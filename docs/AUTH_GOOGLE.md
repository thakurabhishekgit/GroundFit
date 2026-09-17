# Google Auth setup (local)

**Ports:** frontend `2000` · backend `7000`

Flow: React shows “Continue with Google” → Google returns an **ID token** → FastAPI verifies it with Google → upserts user → issues our session/JWT.

---

## 1. Google Cloud Console

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create (or pick) a project — e.g. `GroundFit`
3. **APIs & Services → OAuth consent screen**
   - User type: **External**
   - App name: `GroundFit`
   - User support email: your Gmail
   - Developer contact: same
   - Scopes: leave default (`openid`, `email`, `profile`) — enough
   - Test users: add your Gmail (+ friends’ emails while in **Testing**)
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: **Web application**
   - Name: `GroundFit Web`
   - **Authorized JavaScript origins**
     - `http://localhost:2000`
   - **Authorized redirect URIs**
     - `http://localhost:2000`  
     - (GIS popup/one-tap often only needs the origin; add redirect if you use full redirect flow)
5. Copy **Client ID** and **Client Secret**

---

## 2. Env vars

### Frontend (`apps/web` later) — port 2000

```env
VITE_API_URL=http://localhost:7000
VITE_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com
```

### Backend (`apps/api` later) — port 7000

```env
PORT=7000
FRONTEND_URL=http://localhost:2000
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET
CORS_ORIGINS=http://localhost:2000
JWT_SECRET=change-me-to-a-long-random-string
```

Use the **same** `GOOGLE_CLIENT_ID` on web and API.

---

## 3. What each side does

| Side | Job |
|------|-----|
| Frontend | Load Google Identity Services → get `credential` (JWT ID token) → `POST /auth/google` with `{ "id_token": "..." }` |
| Backend | Verify ID token (`aud` = Client ID, `iss` = Google, email verified) → create/find user → return app JWT / set HTTP-only cookie |

---

## 4. Local checklist

- [ ] Consent screen published as **Testing** + your email as test user
- [ ] JS origin includes `http://localhost:2000` (no trailing slash)
- [ ] Frontend runs on **2000**, API on **7000**
- [ ] CORS allows `http://localhost:2000`

---

## 5. Production (later)

Add Vercel / Render URLs to the same OAuth client:

- Origins: `https://your-app.vercel.app`
- Redirects: `https://your-app.vercel.app`
- Env: same vars with production URLs

Do **not** put `GOOGLE_CLIENT_SECRET` in the frontend.
