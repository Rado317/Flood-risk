<template>
  <Transition name="fade">
    <Welcome3D v-if="showWelcome" @enter="showWelcome = false" />
  </Transition>

  <Transition name="rise">
    <div class="page" v-if="!showWelcome">
      <AmbientBackground :couleur="resultat ? resultat.couleur : '#0ea5e9'" />
      <div class="content">
      <header>
        <div class="brand">
          <div>
            <h1>ARO<span class="dot">.ai</span> — Risque d'Inondation</h1>
            <p class="subtitle">Station Ambohimanambola — Classification selon la hauteur d'eau maximale</p>
          </div>
        </div>
      </header>

      <section class="slider-card">
        <label for="hauteur">Hauteur d'eau maximale mesurée</label>
        <div class="slider-row">
          <input
            id="hauteur"
            type="range"
            min="0"
            :max="seuils.valeur_max"
            step="0.01"
            v-model.number="hauteurMax"
          />
          <span class="value">{{ hauteurMax.toFixed(2) }} m</span>
        </div>
      </section>

      <Transition name="pop" mode="out-in">
        <section class="result" v-if="resultat" :key="resultat.niveau">
          <div class="card" :style="{ backgroundColor: resultat.couleur }">
            <div class="card-label">Niveau de risque</div>
            <div class="card-value">{{ resultat.niveau }}</div>
            <div class="card-sub">hauteur_max = {{ resultat.hauteur_max.toFixed(2) }} m</div>
          </div>
          <div class="gauge-wrap">
            <RiskGauge
              :hauteur="hauteurMax"
              :max="seuils.valeur_max"
              :niveaux="niveauxGauge"
              @update:hauteur="hauteurMax = $event"
            />
            <span class="gauge-hint">glisser sur la jauge pour régler la hauteur</span>
          </div>
        </section>
      </Transition>

      <Transition name="pop">
        <section
          class="alert"
          v-if="resultat"
          :style="{ borderColor: resultat.couleur, backgroundColor: resultat.couleur + '22' }"
        >
          <p>{{ resultat.message }}</p>
        </section>
      </Transition>

      <section class="chat" v-if="resultat">
        <label for="question">Poser une question à l'assistant</label>
        <div class="chat-input-row">
          <input
            id="question"
            v-model="question"
            type="text"
            placeholder="Ex : Qu'est-ce que je dois faire ?"
            @keyup.enter="poserQuestion"
          />
          <button :disabled="chargementChat || !question.trim()" @click="poserQuestion">
            {{ chargementChat ? '...' : 'Demander' }}
          </button>
        </div>
        <Transition name="pop">
          <div v-if="reponseChat" class="chat-response">
            <div>
              <p>{{ reponseChat }}</p>
              <span class="chat-meta">
                réponse basée sur hauteur_max = {{ hauteurALaQuestion.toFixed(2) }} m
              </span>
            </div>
          </div>
        </Transition>
      </section>

      <footer v-if="resultat">
        Seuils : Faible &lt; {{ resultat.seuil_faible }} m ≤ Modéré &lt; {{ resultat.seuil_modere }} m
        ≤ Élevé &lt; {{ resultat.seuil_eleve }} m ≤ Critique
      </footer>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import Welcome3D from './components/Welcome3D.vue'
import AmbientBackground from './components/AmbientBackground.vue'
import RiskGauge from './components/RiskGauge.vue'
import { predireRisque, recupererSeuils, demanderIA } from './services/api'

const showWelcome = ref(true)

const hauteurMax = ref(1.58)
const resultat = ref(null)
const seuils = reactive({ faible: 1.5, modere: 2.0, eleve: 4.05, valeur_max: 4.55 })

const question = ref('')
const reponseChat = ref('')
const chargementChat = ref(false)
const hauteurALaQuestion = ref(0)

const niveauxGauge = ref([
  { borne_sup: 1.5, couleur: '#2DD4BF' },
  { borne_sup: 2.0, couleur: '#F97316' },
  { borne_sup: 4.05, couleur: '#F87171' },
  { borne_sup: Infinity, couleur: '#7F1D1D' },
])

async function actualiser() {
  try {
    resultat.value = await predireRisque({
      hauteur_max: hauteurMax.value,
      generer_message_ia: false,
    })
  } catch (err) {
    console.error('Erreur API', err)
  }
}

async function poserQuestion() {
  if (!question.value.trim()) return
  chargementChat.value = true
  reponseChat.value = ''
  const hauteurEnvoyee = hauteurMax.value
  try {
    const data = await demanderIA({
      question: question.value.trim(),
      hauteur_max: hauteurEnvoyee,
    })
    reponseChat.value = data.reponse
    hauteurALaQuestion.value = hauteurEnvoyee
  } catch (err) {
    console.error('Erreur chat IA', err)
    reponseChat.value = "Impossible de contacter l'assistant IA pour le moment."
    hauteurALaQuestion.value = hauteurEnvoyee
  } finally {
    chargementChat.value = false
  }
}

let timer = null
watch(hauteurMax, () => {
  clearTimeout(timer)
  timer = setTimeout(actualiser, 200)
})

onMounted(async () => {
  try {
    const data = await recupererSeuils()
    Object.assign(seuils, data)
  } catch (err) {
    console.warn('Seuils par défaut utilisés (backend indisponible)', err)
  }
  actualiser()
})
</script>

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
  overflow: hidden;
}
.content {
  position: relative;
  z-index: 1;
  max-width: 760px;
  margin: 0 auto;
  padding: 40px 24px 60px;
  font-family: system-ui, sans-serif;
  color: #0f172a;
}
header {
  margin-bottom: 28px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
h1 {
  font-size: 24px;
  margin: 0;
}
.dot {
  color: #0ea5e9;
}
.subtitle {
  color: #64748b;
  margin: 4px 0 0;
  font-size: 14px;
}

.slider-card {
  background: white;
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
  margin-bottom: 24px;
}
.slider-card label {
  font-weight: 600;
  font-size: 14px;
  color: #334155;
}
.slider-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 12px;
}
.slider-row input[type='range'] {
  flex: 1;
  accent-color: #0ea5e9;
  height: 6px;
}
.slider-row .value {
  font-weight: 700;
  min-width: 64px;
  text-align: right;
}

.result {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.gauge-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.gauge-hint {
  font-size: 11px;
  color: #94a3b8;
}
.card {
  border-radius: 16px;
  padding: 26px;
  color: white;
  flex: 1;
  min-width: 220px;
  text-align: center;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  transition: background-color 0.4s ease;
}
.card-label {
  font-size: 14px;
  opacity: 0.9;
}
.card-value {
  font-size: 34px;
  font-weight: 800;
  margin: 8px 0;
}
.card-sub {
  font-size: 13px;
  opacity: 0.85;
}

.alert {
  border-left: 4px solid;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 20px;
}

.chat {
  background: white;
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
  margin-bottom: 20px;
}
.chat label {
  display: block;
  margin-bottom: 10px;
  font-weight: 600;
  font-size: 14px;
  color: #334155;
}
.chat-input-row {
  display: flex;
  gap: 8px;
}
.chat-input-row input {
  flex: 1;
  padding: 11px 14px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
}
.chat-input-row input:focus {
  outline: none;
  border-color: #0ea5e9;
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.15);
}
.chat-input-row button {
  padding: 11px 18px;
  border-radius: 10px;
  border: none;
  background: #0f172a;
  color: white;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s ease;
}
.chat-input-row button:hover:not(:disabled) {
  background: #0ea5e9;
}
.chat-input-row button:disabled {
  opacity: 0.5;
  cursor: default;
}
.chat-response {
  margin-top: 14px;
  padding: 14px 16px;
  background: #f1f5f9;
  border-radius: 10px;
  display: flex;
  gap: 10px;
}
.chat-response p {
  margin: 0;
  font-style: italic;
  line-height: 1.5;
}
.chat-meta {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  color: #94a3b8;
  font-style: normal;
}

footer {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.rise-enter-active {
  transition: all 0.6s ease;
}
.rise-enter-from {
  opacity: 0;
  transform: translateY(16px);
}

.pop-enter-active {
  transition: all 0.3s ease;
}
.pop-enter-from {
  opacity: 0;
  transform: scale(0.97);
}
</style>