# Quick Start - Mini-TUG Deployment

## Snelle Deployment (5 minuten)

### Stap 1: Backend op Render (2 min)

1. Ga naar [render.com](https://render.com) en maak account
2. Klik **"New +"** → **"Web Service"**
3. Verbind GitHub repo
4. Settings:
   - **Name**: `mini-tug-backend`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.api:app --host 0.0.0.0 --port $PORT`
5. Environment Variables toevoegen:
   ```
   TUG_ALLOWED_ORIGINS=http://localhost:3000
   TUG_DOCAI_KEY_JSON=<je JSON credentials>
   ```
6. Klik **"Create Web Service"**
7. **Wacht op deploy** en noteer URL (bijv. `https://mini-tug-backend.onrender.com`)

### Stap 2: Frontend op Vercel (2 min)

1. Ga naar [vercel.com](https://vercel.com) en maak account
2. Klik **"Add New..."** → **"Project"**
3. Import GitHub repo
4. Settings:
   - **Root Directory**: `frontend`
   - **Framework**: Next.js (auto-detect)
5. Environment Variable:
   ```
   NEXT_PUBLIC_API_URL=https://mini-tug-backend.onrender.com
   ```
   (Vervang met je echte Render URL!)
6. Klik **"Deploy"**
7. **Wacht op deploy** en noteer URL (bijv. `https://mini-tug.vercel.app`)

### Stap 3: CORS Fix (1 min)

1. Ga terug naar Render dashboard
2. Update `TUG_ALLOWED_ORIGINS`:
   ```
   TUG_ALLOWED_ORIGINS=https://mini-tug.vercel.app,http://localhost:3000
   ```
   (Vervang met je echte Vercel URL!)
3. Render deployt automatisch opnieuw

### Klaar! 🎉

Je app is nu live op je Vercel URL!

---

## Lokale Test (Optioneel)

### Backend lokaal:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.api:app --reload
```

### Frontend lokaal:
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Troubleshooting

**Backend werkt niet?**
- Check Render logs
- Test: `curl https://your-backend.onrender.com/healthz`

**Frontend kan backend niet bereiken?**
- Check `NEXT_PUBLIC_API_URL` in Vercel
- Check CORS in Render (`TUG_ALLOWED_ORIGINS`)

**Build faalt?**
- Check logs in Render/Vercel dashboard
- Test lokaal eerst: `npm run build` (frontend) of `pip install -r requirements.txt` (backend)

