"""Backend FastAPI — Analyse et alerte du risque d'inondation.

Classification directe par seuils sur Hauteur_max, complétée par la
probabilité d'un modèle ML (.pkl) si disponible, et par des réponses
générées via l'API Groq (LLM hébergé, gratuit) — utilisée ici en
remplacement d'un LLM local (Ollama) pour permettre le déploiement sur
Render sans VPS dédié. Repasser à Ollama en local reste possible pour
respecter la contrainte initiale « sans appel API externe ».
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import httpx
import joblib
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flood-risk-api")

app = FastAPI(title="API Risque d'Inondation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://flood-risk-six.vercel.app",
    ],
    allow_origin_regex=r"https://flood-risk.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Seuils (à ajuster selon les données réelles de la station)
# --------------------------------------------------------------------------
SEUIL_FAIBLE = 1.50
SEUIL_MODERE = 2.00
SEUIL_ELEVE = 4.05
VALEUR_MAX = 4.55

NIVEAUX = [
    {"nom": "Faible", "borne_sup": SEUIL_FAIBLE, "couleur": "#2DD4BF",
     "message": "Aucune alerte à signaler. Surveillance de routine."},
    {"nom": "Modéré", "borne_sup": SEUIL_MODERE, "couleur": "#F97316",
     "message": "Vigilance recommandée. Suivez l'évolution sur les prochaines heures."},
    {"nom": "Élevé", "borne_sup": SEUIL_ELEVE, "couleur": "#F87171",
     "message": "Risque élevé. Informez les équipes de terrain (BNGRC/APIPA)."},
    {"nom": "Critique", "borne_sup": float("inf"), "couleur": "#7F1D1D",
     "message": "ALERTE CRITIQUE. Déclenchez la procédure d'urgence."},
]

MODEL_PATH = Path(__file__).parent / "models" / "pipeline.pkl"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

_model_package: Optional[dict] = None


def get_model_package() -> Optional[dict]:
    global _model_package
    if _model_package is None and MODEL_PATH.exists():
        try:
            _model_package = joblib.load(MODEL_PATH)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Impossible de charger le modèle : %s", exc)
    return _model_package


class HauteurInput(BaseModel):
    hauteur_max: float = Field(..., ge=0, description="Hauteur d'eau maximale mesurée (m)")
    hauteur_mean: Optional[float] = None
    debit_mean: Optional[float] = None
    pluie_somme: Optional[float] = None
    generer_message_ia: bool = False


class RiskOutput(BaseModel):
    niveau: str
    couleur: str
    message: str
    hauteur_max: float
    seuil_faible: float
    seuil_modere: float
    seuil_eleve: float
    probabilite_modele: Optional[float] = None
    message_ia: Optional[str] = None


def classifier_seuil(hauteur: float) -> dict:
    for niveau in NIVEAUX:
        if hauteur < niveau["borne_sup"]:
            return niveau
    return NIVEAUX[-1]


async def appeler_ollama(prompt: str) -> Optional[str]:
    """Envoie un prompt à l'API Groq (LLM hébergé, gratuit) et retourne sa réponse."""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY absente — configure-la dans les variables d'environnement.")
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 300,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Groq indisponible : %s", exc)
        return None


async def generer_message_ia(niveau: str, hauteur: float) -> Optional[str]:
    """Génère un message d'alerte contextualisé via un LLM local (Ollama)."""
    prompt = (
        "Tu es un système d'alerte inondation pour la station d'Ambohimanambola "
        f"à Madagascar. Le niveau de risque actuel est '{niveau}' avec une hauteur "
        f"d'eau de {hauteur:.2f} m. Rédige en français un message d'alerte court "
        "(3 phrases maximum), clair et actionnable pour les autorités locales "
        "(BNGRC/APIPA)."
    )
    return await appeler_ollama(prompt)


class ChatInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    hauteur_max: float = Field(..., ge=0, description="Hauteur d'eau actuelle affichée à l'utilisateur")


class ChatOutput(BaseModel):
    reponse: str
    niveau: str


@app.post("/api/chat", response_model=ChatOutput)
async def chat(payload: ChatInput) -> ChatOutput:
    niveau = classifier_seuil(payload.hauteur_max)

    prompt = (
        "Tu es un assistant d'alerte inondation pour la station d'Ambohimanambola "
        "à Madagascar, utilisé par des habitants et des agents du BNGRC/APIPA. "
        f"Contexte actuel : hauteur d'eau mesurée = {payload.hauteur_max:.2f} m, "
        f"niveau de risque = '{niveau['nom']}' "
        f"(seuils : Faible < {SEUIL_FAIBLE} m, Modéré < {SEUIL_MODERE} m, "
        f"Élevé < {SEUIL_ELEVE} m, au-delà = Critique). "
        f"Question de l'utilisateur : \"{payload.question}\". "
        "Réponds en français, de façon claire, concrète et rassurante mais honnête, "
        "en 4 phrases maximum, en tenant compte du niveau de risque actuel."
    )

    reponse = await appeler_ollama(prompt)
    if reponse is None:
        reponse = (
            "L'assistant IA local (Ollama) n'est pas disponible actuellement. "
            f"En attendant, voici le conseil standard pour le niveau '{niveau['nom']}' : "
            f"{niveau['message']}"
        )

    return ChatOutput(reponse=reponse, niveau=niveau["nom"])


@app.get("/", response_class=HTMLResponse)
def accueil() -> str:
    return """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8" />
<title>API Risque d'Inondation — ARO.ai</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, sans-serif;
    background: radial-gradient(circle at 50% 0%, #0f172a, #020617 70%);
    color: #e2e8f0;
    min-height: 100vh;
    padding: 40px 20px;
  }
  .wrap { max-width: 640px; margin: 0 auto; }
  h1 { font-size: 28px; margin: 0 0 4px; }
  .dot { color: #38bdf8; }
  p.sub { color: #94a3b8; margin: 0 0 32px; font-size: 14px; }
  .status { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: #34d399; margin-bottom: 32px; }
  .status .light { width: 8px; height: 8px; border-radius: 50%; background: #34d399; }
  .card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 22px;
    margin-bottom: 20px;
  }
  .card h2 { font-size: 15px; margin: 0 0 14px; color: #f1f5f9; }
  label { display: block; font-size: 13px; color: #94a3b8; margin-bottom: 6px; }
  input[type="range"] { width: 100%; accent-color: #38bdf8; }
  input[type="text"], input[type="number"] {
    width: 100%; padding: 10px 12px; border-radius: 8px;
    border: 1px solid #334155; background: #0f172a; color: #e2e8f0; font-size: 14px;
  }
  .row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
  .row .val { font-weight: 700; min-width: 60px; text-align: right; }
  button {
    padding: 10px 18px; border-radius: 8px; border: none;
    background: #38bdf8; color: #020617; font-weight: 600; cursor: pointer;
    margin-top: 12px;
  }
  button:hover { background: #7dd3fc; }
  button:disabled { opacity: 0.5; cursor: default; }
  .result { margin-top: 16px; padding: 14px; border-radius: 10px; background: #0f172a; font-size: 14px; line-height: 1.5; white-space: pre-wrap; }
  .links { font-size: 13px; color: #64748b; }
  .links a { color: #38bdf8; text-decoration: none; }
  .links a:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="wrap">
  <h1>ARO<span class="dot">.ai</span> — API</h1>
  <p class="sub">Backend de classification et d'alerte du risque d'inondation — station Ambohimanambola</p>
  <div class="status"><span class="light"></span> Service actif</div>

  <div class="card">
    <h2>Tester la classification</h2>
    <label for="hauteur">Hauteur d'eau maximale (m)</label>
    <div class="row">
      <input type="range" id="hauteur" min="0" max="4.55" step="0.01" value="1.58" />
      <span class="val" id="hauteurVal">1.58 m</span>
    </div>
    <button id="btnPredict">Tester /api/predict</button>
    <div class="result" id="resultPredict" style="display:none;"></div>
  </div>

  <div class="card">
    <h2>Tester l'assistant IA</h2>
    <label for="question">Question</label>
    <input type="text" id="question" placeholder="Qu'est-ce que je dois faire ?" />
    <button id="btnChat">Tester /api/chat</button>
    <div class="result" id="resultChat" style="display:none;"></div>
  </div>

  <p class="links">
    Documentation interactive : <a href="/docs">/docs</a> —
    Etat du service : <a href="/api/health">/api/health</a>
  </p>
</div>

<script>
  const hauteurInput = document.getElementById('hauteur');
  const hauteurVal = document.getElementById('hauteurVal');
  hauteurInput.addEventListener('input', () => {
    hauteurVal.textContent = parseFloat(hauteurInput.value).toFixed(2) + ' m';
  });

  document.getElementById('btnPredict').addEventListener('click', async (e) => {
    const btn = e.target;
    const box = document.getElementById('resultPredict');
    btn.disabled = true;
    box.style.display = 'block';
    box.textContent = 'Chargement...';
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hauteur_max: parseFloat(hauteurInput.value) }),
      });
      const data = await res.json();
      box.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      box.textContent = 'Erreur : ' + err;
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById('btnChat').addEventListener('click', async (e) => {
    const btn = e.target;
    const box = document.getElementById('resultChat');
    const question = document.getElementById('question').value.trim();
    if (!question) return;
    btn.disabled = true;
    box.style.display = 'block';
    box.textContent = 'Chargement...';
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, hauteur_max: parseFloat(hauteurInput.value) }),
      });
      const data = await res.json();
      box.textContent = data.reponse || JSON.stringify(data, null, 2);
    } catch (err) {
      box.textContent = 'Erreur : ' + err;
    } finally {
      btn.disabled = false;
    }
  });
</script>
</body>
</html>
"""


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "modele_charge": get_model_package() is not None}


@app.get("/api/seuils")
def seuils() -> dict:
    return {
        "seuil_faible": SEUIL_FAIBLE,
        "seuil_modere": SEUIL_MODERE,
        "seuil_eleve": SEUIL_ELEVE,
        "valeur_max": VALEUR_MAX,
    }


@app.post("/api/predict", response_model=RiskOutput)
async def predict(payload: HauteurInput) -> RiskOutput:
    niveau = classifier_seuil(payload.hauteur_max)

    probabilite_modele = None
    package = get_model_package()
    if package is not None and payload.hauteur_mean is not None:
        try:
            features = package["feature_cols"]
            row = {
                "Hauteur_max": payload.hauteur_max,
                "Hauteur_mean": payload.hauteur_mean,
                "Débit_mean": payload.debit_mean,
                "pluie_somme": payload.pluie_somme,
            }
            X = np.array([[row.get(f, 0.0) for f in features]])
            probabilite_modele = float(package["pipeline"].predict_proba(X)[0, 1])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Prédiction modèle impossible : %s", exc)

    message_ia = None
    if payload.generer_message_ia:
        message_ia = await generer_message_ia(niveau["nom"], payload.hauteur_max)

    return RiskOutput(
        niveau=niveau["nom"],
        couleur=niveau["couleur"],
        message=niveau["message"],
        hauteur_max=payload.hauteur_max,
        seuil_faible=SEUIL_FAIBLE,
        seuil_modere=SEUIL_MODERE,
        seuil_eleve=SEUIL_ELEVE,
        probabilite_modele=probabilite_modele,
        message_ia=message_ia,
    )