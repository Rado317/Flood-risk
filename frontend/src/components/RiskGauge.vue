<template>
  <svg viewBox="0 0 300 170" class="gauge">
    <path v-for="(zone, i) in zones" :key="i" :d="zone.path" :fill="zone.color" />
    <line
      :x1="150" :y1="150"
      :x2="needlePoint.x" :y2="needlePoint.y"
      stroke="#111827" stroke-width="4" stroke-linecap="round"
    />
    <circle cx="150" cy="150" r="8" fill="#111827" />
    <text x="150" y="165" text-anchor="middle" class="value-text">
      {{ hauteur.toFixed(2) }} m
    </text>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  hauteur: { type: Number, required: true },
  max: { type: Number, default: 4.55 },
  niveaux: { type: Array, required: true }, // [{ borne_sup, couleur }]
})

function polarToCartesian(cx, cy, r, angleDeg) {
  const angleRad = ((angleDeg - 180) * Math.PI) / 180
  return { x: cx + r * Math.cos(angleRad), y: cy + r * Math.sin(angleRad) }
}

function arcPath(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1
  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y} Z`
}

const zones = computed(() => {
  let lower = 0
  const result = []
  for (const niveau of props.niveaux) {
    const upper = Math.min(niveau.borne_sup, props.max)
    const startAngle = (lower / props.max) * 180
    const endAngle = (upper / props.max) * 180
    result.push({ path: arcPath(150, 150, 130, startAngle, endAngle), color: niveau.couleur })
    lower = upper
    if (lower >= props.max) break
  }
  return result
})

const needleAngle = computed(() => (Math.min(props.hauteur, props.max) / props.max) * 180)
const needlePoint = computed(() => polarToCartesian(150, 150, 110, needleAngle.value))
</script>

<style scoped>
.gauge {
  width: 100%;
  max-width: 320px;
}
.value-text {
  font-size: 20px;
  font-weight: 700;
  fill: #111827;
}
</style>
