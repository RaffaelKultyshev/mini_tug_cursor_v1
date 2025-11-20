# Deployment Guide - Mini-TUG

Deze guide helpt je om Mini-TUG te deployen naar Render (backend) en Vercel (frontend).

## Stap 1: Backend deployen naar Render

### 1.1 Voorbereiding

1. **Push je code naar GitHub** (als je dat nog niet hebt gedaan):
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Maak een Render account** op [render.com](https://render.com)

### 1.2 Render Service aanmaken

1. Ga naar [Render Dashboard](https://dashboard.render.com)
2. Klik op **"New +"** → **"Web Service"**
3. Verbind je GitHub repository
4. Kies de repository met Mini-TUG

### 1.3 Render Configuratie

**Service Settings:**
- **Name**: `mini-tug-backend`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r backend/requirements.txt`
- **Start Command**: `uvicorn backend.api:app --host 0.0.0.0 --port $PORT`
- **Plan**: Kies een gratis plan (of betaald als je meer resources nodig hebt)

**Environment Variables** (in Render dashboard):
```
TUG_ALLOWED_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
TUG_DOCAI_KEY_JSON=<je volledige JSON credentials als string>
TUG_DOCAI_PROJECT_ID=361271679946
TUG_DOCAI_LOCATION=eu
TUG_DOCAI_PROCESSOR_ID=2ee67d07894fd7f1
```

**Belangrijk**: 
- Voor `TUG_DOCAI_KEY_JSON`: Kopieer de volledige inhoud van je `tug-docai-key.json` bestand en plak het als één string (escape quotes met `\"` of gebruik base64 encoding)
- Voor `TUG_ALLOWED_ORIGINS`: Voeg je Vercel frontend URL toe zodra je die hebt

### 1.4 Deploy

1. Klik op **"Create Web Service"**
2. Render bouwt en deployt automatisch
3. Wacht tot de deploy klaar is
4. **Noteer je backend URL** (bijv. `https://mini-tug-backend.onrender.com`)

### 1.5 Test Backend

Test of je backend werkt:
```bash
curl https://your-backend-url.onrender.com/healthz
```

Je zou moeten zien: `{"status":"ok","has_data":false}`

---

## Stap 2: Frontend deployen naar Vercel

### 2.1 Voorbereiding

1. **Zorg dat je code op GitHub staat**

2. **Maak een Vercel account** op [vercel.com](https://vercel.com)

### 2.2 Vercel Project aanmaken

1. Ga naar [Vercel Dashboard](https://vercel.com/dashboard)
2. Klik op **"Add New..."** → **"Project"**
3. Import je GitHub repository
4. Selecteer de repository

### 2.3 Vercel Configuratie

**Framework Preset**: Next.js (automatisch gedetecteerd)

**Root Directory**: `frontend` (als je frontend in een subdirectory staat)

**Environment Variables**:
```
NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
```

**Belangrijk**: Vervang `your-backend-url.onrender.com` met je echte Render backend URL!

### 2.4 Deploy

1. Klik op **"Deploy"**
2. Vercel bouwt en deployt automatisch
3. Wacht tot de deploy klaar is
4. **Noteer je frontend URL** (bijv. `https://mini-tug.vercel.app`)

### 2.5 Update Backend CORS

1. Ga terug naar Render dashboard
2. Update de `TUG_ALLOWED_ORIGINS` environment variable:
   ```
   TUG_ALLOWED_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
   ```
3. Render zal automatisch opnieuw deployen

---

## Stap 3: Test je Live App

1. Ga naar je Vercel frontend URL
2. Test of de app werkt:
   - KPI's laden
   - Sample data laden
   - CSV uploaden
   - OCR scannen (als je Document AI key hebt geconfigureerd)

---

## Troubleshooting

### Backend start niet
- Check de logs in Render dashboard
- Zorg dat alle environment variables zijn ingesteld
- Check of `uvicorn` correct is geïnstalleerd

### CORS errors
- Zorg dat `TUG_ALLOWED_ORIGINS` je Vercel URL bevat
- Check of de backend URL correct is in `NEXT_PUBLIC_API_URL`

### OCR werkt niet
- Check of `TUG_DOCAI_KEY_JSON` correct is geformatteerd (escape quotes!)
- Test of je Document AI processor actief is in Google Cloud Console

### Frontend kan backend niet bereiken
- Check of `NEXT_PUBLIC_API_URL` correct is ingesteld in Vercel
- Test de backend URL direct in je browser: `https://your-backend.onrender.com/healthz`

---

## Custom Domain (Optioneel)

### Vercel Domain
1. Ga naar je project in Vercel dashboard
2. Klik op **"Settings"** → **"Domains"**
3. Voeg je custom domain toe
4. Volg de DNS instructies

### Render Domain
1. Ga naar je service in Render dashboard
2. Klik op **"Settings"** → **"Custom Domain"**
3. Voeg je custom domain toe
4. Update DNS records volgens instructies

---

## Kosten

- **Render Free Tier**: 750 uur/maand gratis (genoeg voor development)
- **Vercel Free Tier**: Onbeperkt voor persoonlijke projecten
- **Totaal**: Gratis voor development/testing!

---

## Support

Als je problemen hebt:
1. Check de logs in Render/Vercel dashboards
2. Test endpoints handmatig met `curl` of Postman
3. Check of alle environment variables correct zijn ingesteld

