<template>
  <div class="page">
    <header>
      <h1>🌊 Classification du Risque d'Inondation</h1>
      <p class="subtitle">
        Station Ambohimanambola — Classification selon la hauteur d'eau maximale
      </p>
    </header>

    <section class="slider-section">
      <label for="hauteur">Hauteur d'eau maximale mesurée (m)</label>
      <input
        id="hauteur"
        type="range"
        min="0"
        :max="seuils.valeur_max"
        step="0.01"
        v-model.number="hauteurMax"
      />
      <span class="value">{{ hauteurMax.toFixed(2) }} m</span>
    </section>

    <section class="result" v-if="resultat">
      <div class="card" :style="{ backgroundColor: resultat.couleur }">
        <div class="card-label">Niveau de risque</div>
        <div class="card-value">{{ resultat.niveau }}</div>
        <div class="card-sub">hauteur_max = {{ resultat.hauteur_max.toFixed(2) }} m</div>
      </div>
      <RiskGauge :hauteur="hauteurMax" :max="seuils.valeur_max" :niveaux="niveauxGauge" />
    </section>

    <section
      class="alert"
      v-if="resultat"
      :style="{ borderColor: resultat.couleur, backgroundColor: resultat.couleur + '22' }"
    >
      <p>{{ resultat.message }}</p>
      <p v-if="resultat.message_ia" class="ia-message">🤖 {{ resultat.message_ia }}</p>
      <button class="ia-button" :disabled="chargementIA" @click="genererMessageIA">
        {{ chargementIA ? 'Génération...' : "Générer un message d'alerte via l'IA locale" }}
      </button>
    </section>

    <footer v-if="resultat">
      Seuils : Faible &lt; {{ resultat.seuil_faible }} m ≤ Modéré &lt; {{ resultat.seuil_modere }} m
      ≤ Élevé &lt; {{ resultat.seuil_eleve }} m ≤ Critique
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import RiskGauge from './components/RiskGauge.vue'
import { predireRisque, recupererSeuils } from './services/api'

const hauteurMax = ref(1.58)
const resultat = ref(null)
const chargementIA = ref(false)
const seuils = reactive({ faible: 1.5, modere: 2.0, eleve: 4.05, valeur_max: 4.55 })

const niveauxGauge = ref([
  { borne_sup: 1.5, couleur: '#2DD4BF' },
  { borne_sup: 2.0, couleur: '#F97316' },
  { borne_sup: 4.05, couleur: '#F87171' },
  { borne_sup: Infinity, couleur: '#7F1D1D' },
])

async function actualiser(avecIA = false) {
  try {
    resultat.value = await predireRisque({
      hauteur_max: hauteurMax.value,
      generer_message_ia: avecIA,
    })
  } catch (err) {
    console.error('Erreur API', err)
  } finally {
    chargementIA.value = false
  }
}

async function genererMessageIA() {
  chargementIA.value = true
  await actualiser(true)
}

let timer = null
watch(hauteurMax, () => {
  clearTimeout(timer)
  timer = setTimeout(() => actualiser(false), 200)
})

onMounted(async () => {
  try {
    const data = await recupererSeuils()
    Object.assign(seuils, data)
  } catch (err) {
    console.warn('Seuils par défaut utilisés (backend indisponible)', err)
  }
  actualiser(false)
})
</script>

<style scoped>
.page {
  max-width: 720px;
  margin: 40px auto;
  padding: 24px;
  font-family: system-ui, sans-serif;
  color: #111827;
}
.subtitle {
  color: #6b7280;
  margin-top: -8px;
}
.slider-section {
  margin: 24px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.slider-section label {
  flex-shrink: 0;
}
.slider-section input[type='range'] {
  flex: 1;
}
.result {
  display: flex;
  gap: 24px;
  align-items: center;
  flex-wrap: wrap;
}
.card {
  border-radius: 12px;
  padding: 24px;
  color: white;
  flex: 1;
  min-width: 220px;
  text-align: center;
}
.card-label {
  font-size: 14px;
}
.card-value {
  font-size: 32px;
  font-weight: 700;
  margin: 8px 0;
}
.alert {
  border-left: 4px solid;
  border-radius: 6px;
  padding: 14px 18px;
  margin-top: 16px;
}
.ia-message {
  margin-top: 8px;
  font-style: italic;
}
.ia-button {
  margin-top: 10px;
  padding: 8px 14px;
  border-radius: 6px;
  border: none;
  background: #111827;
  color: white;
  cursor: pointer;
}
.ia-button:disabled {
  opacity: 0.6;
  cursor: default;
}
footer {
  margin-top: 16px;
  color: #6b7280;
  font-size: 13px;
}
</style>
