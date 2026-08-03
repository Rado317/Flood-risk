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