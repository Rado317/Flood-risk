# Risque d'Inondation — Vue.js + FastAPI

## Lancer le backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Place ton modèle entraîné dans `backend/models/pipeline.pkl` (optionnel —
sans lui, seul le seuillage direct sur `hauteur_max` est utilisé).

Pour activer les messages générés par IA, installe et lance Ollama en local :

```bash
ollama serve
ollama pull llama3.1
```

## Lancer le frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvre http://localhost:5173 — l'app appelle l'API sur http://localhost:8000.

## Déploiement

- **Frontend (Vue)** : déployable tel quel sur Vercel (`npm run build`, dossier `dist`).
- **Backend (FastAPI + Ollama)** : Vercel ne convient pas (fonctions serverless
  éphémères, incompatibles avec un process Ollama persistant). Héberge le
  backend sur un VPS, Render, Railway (avec Docker) ou en local/sur le serveur
  de la fac, puis pointe `VITE_API_URL` du frontend vers son URL.
# Flood-risk
