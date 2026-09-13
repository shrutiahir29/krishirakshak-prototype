# Deploying KrishiRakshak — Render (backend) + Vercel (frontend)

## 1. Push code to GitHub
Two options:
- One repo with `backend/` and `frontend-deploy/` as subfolders (recommended, simplest)
- Two separate repos (also fine, just adjust the "root directory" settings below)

```bash
git init
git add .
git commit -m "KrishiRakshak prototype"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

---

## 2. Deploy the backend on Render

1. Go to https://render.com → **New** → **Web Service**
2. Connect your GitHub repo
3. If using one repo with subfolders, set **Root Directory** to `backend`
4. Render should auto-detect `render.yaml` and pre-fill these — verify they match:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
5. Add an environment variable (Settings → Environment):
   - `ALLOWED_ORIGINS` = `https://<your-vercel-app>.vercel.app,http://localhost:3000`
   (You can add this now with a placeholder and update it after step 3, once you know your real Vercel URL.)
6. Click **Deploy**. Render will give you a URL like:
   `https://krishirakshak-api.onrender.com`
7. Verify it's alive: open `https://krishirakshak-api.onrender.com/health` in your browser — should return `{"status":"healthy"}`. Also check `/docs` for the interactive API explorer.

**Note on the free tier:** Render's free web services sleep after 15 minutes of inactivity. The first request after sleeping takes ~30-50 seconds to wake up — this is normal, not a bug. Upgrade to a paid instance later if you need always-on.

---

## 3. Deploy the frontend on Vercel

1. Go to https://vercel.com → **Add New** → **Project**
2. Import the same GitHub repo
3. If using one repo with subfolders, set **Root Directory** to `frontend-deploy`
4. Framework Preset: choose **Other** (it's a static HTML file, no build step needed)
5. Click **Deploy**. Vercel gives you a URL like:
   `https://krishirakshak.vercel.app`

---

## 4. Connect the two

1. Open `frontend-deploy/index.html`, find this line near the top of the `<script>`:
   ```js
   const RENDER_URL_PLACEHOLDER = "https://krishirakshak-api.onrender.com";
   ```
   Replace it with your **actual** Render URL from step 2.
2. Commit and push — Vercel auto-redeploys on every push to `main`.
3. Go back to Render → Environment → update `ALLOWED_ORIGINS` to include your **actual** Vercel URL from step 3. Redeploy the backend (Render does this automatically when env vars change, or trigger manually via "Manual Deploy").

---

## 5. Verify end-to-end

Open your Vercel URL in a browser. The dashboard should load and show real weather-driven predictions (not the demo/mock fallback data) — if you still see "demo data (backend not reachable)" notes on the cards, double check:
- The Render URL in `index.html` is correct and has no trailing slash
- `ALLOWED_ORIGINS` on Render includes your exact Vercel domain (https, no trailing slash)
- The Render service is awake (visit `/health` directly first to wake it up)

---

## Local development (unaffected by any of this)

Nothing changes for local dev — `API_BASE` auto-detects `localhost` and points at `http://localhost:8000`. Just run:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
and open `frontend-deploy/index.html` directly in your browser.

---

## Optional: Docker instead of Render's native Python runtime

A `Dockerfile` is included in `backend/` if you'd rather deploy via Docker (Render, Fly.io, Railway, or any container host all support this):
```bash
docker build -t krishirakshak-api .
docker run -p 8000:8000 krishirakshak-api
```
