# Lokale Setup - Mini-TUG

## Backend lokaal draaien

1. **Activeer virtual environment:**
   ```bash
   cd backend
   source .venv/bin/activate  # Mac/Linux
   # of: .venv\Scripts\activate  # Windows
   ```

2. **Start de server:**
   ```bash
   # Vanuit de root directory:
   cd /Users/raffael/Desktop/STAGE/TUG
   source backend/.venv/bin/activate
   uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
   ```

   Of gebruik het test script:
   ```bash
   ./test_backend.sh
   ```

3. **Test de backend:**
   - Open: http://127.0.0.1:8000/healthz
   - API docs: http://127.0.0.1:8000/docs

## Frontend lokaal draaien

1. **Installeer dependencies (al gedaan):**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open in browser:**
   - Frontend: http://localhost:3000
   - Zorg dat backend draait op http://127.0.0.1:8000

## Environment Variables

**Backend** (optioneel, voor Document AI):
```bash
export TUG_DOCAI_KEY_JSON='{"type":"service_account",...}'
export TUG_ALLOWED_ORIGINS=http://localhost:3000
```

**Frontend** (optioneel):
```bash
# Maak .env.local in frontend/
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Testen

- Backend health: `curl http://127.0.0.1:8000/healthz`
- Frontend: Open http://localhost:3000
- Test KPI endpoint: `curl http://127.0.0.1:8000/kpi`

## Troubleshooting

**Backend start niet:**
- Check of venv geactiveerd is
- Check of je vanuit root directory draait (niet vanuit backend/)
- Check Python versie: `python3 --version` (moet 3.12+ zijn)

**Frontend kan backend niet bereiken:**
- Check of backend draait op port 8000
- Check CORS settings in backend/config.py
- Check NEXT_PUBLIC_API_URL in frontend

**Import errors:**
- Backend: Zorg dat je vanuit root directory draait
- Frontend: Run `npm install` opnieuw

