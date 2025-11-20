# Mini-TUG Web Stack

Deze repo bevat zowel de FastAPI-backend als de Next.js-frontend van Mini-TUG – een herbouwde versie van de oorspronkelijke Streamlit-app.

## Structuur

- `backend/` – FastAPI-app (`uvicorn backend.api:app`) plus services voor OCR, reconciliatie en rapportages.
- `frontend/` – Next.js (App Router) dashboard dat alle flows uit Streamlit afdekt.
- `assets/`, `notes/`, `notebooks/` – documentatie en referentiemateriaal.

## Lokale setup

1. **Backend**
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn backend.api:app --reload
   ```
   Optioneel: stel `TUG_DOC_AI_KEY_JSON` of `TUG_DOC_AI_KEY_PATH` in voor Google Document AI.

2. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Zet `NEXT_PUBLIC_API_URL` (bijv. via `.env.local`) naar de backend-url.

## Deploy

**🚀 Snelle deployment (5 minuten):** Zie [QUICK_START.md](./QUICK_START.md)

**📖 Uitgebreide deployment guide:** Zie [DEPLOY.md](./DEPLOY.md)

### Overzicht:
- **Backend** → Deploy naar Render (gratis tier beschikbaar)
  - Dockerfile en render.yaml zijn al aanwezig
  - Stel environment variables in: `TUG_DOCAI_KEY_JSON`, `TUG_ALLOWED_ORIGINS`
- **Frontend** → Deploy naar Vercel (gratis tier beschikbaar)
  - vercel.json is al geconfigureerd
  - Stel `NEXT_PUBLIC_API_URL` in naar je Render backend URL
- **Custom domain** → Optioneel via Vercel/Render settings
