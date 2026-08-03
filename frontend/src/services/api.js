import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

export function predireRisque(payload) {
  return api.post('/api/predict', payload).then((r) => r.data)
}

export function recupererSeuils() {
  return api.get('/api/seuils').then((r) => r.data)
}
