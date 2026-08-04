<template>
  <svg
    viewBox="0 0 300 170"
    class="gauge"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointerleave="onPointerUp"
  >
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
import { computed, ref } from 'vue'

const props = defineProps({
  hauteur: { type: Number, required: true },
  max: { type: Number, default: 4.55 },
  niveaux: { type: Array, required: true }, // [{ borne_sup, couleur }]
})

const emit = defineEmits(['update:hauteur'])

const dragging = ref(false)

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

function angleFromPointer(event, svgEl) {
  const rect = svgEl.getBoundingClientRect()
  const scaleX = 300 / rect.width
  const scaleY = 170 / rect.height
  const x = (event.clientX - rect.left) * scaleX - 150
  const y = (event.clientY - rect.top) * scaleY - 150
  let angle = (Math.atan2(y, x) * 180) / Math.PI + 180
  angle = Math.max(0, Math.min(180, angle))
  return angle
}

function updateFromEvent(event) {
  const angle = angleFromPointer(event, event.currentTarget)
  const nouvelleHauteur = (angle / 180) * props.max
  emit('update:hauteur', Math.round(nouvelleHauteur * 100) / 100)
}

function onPointerDown(event) {
  dragging.value = true
  updateFromEvent(event)
}
function onPointerMove(event) {
  if (dragging.value) updateFromEvent(event)
}
function onPointerUp() {
  dragging.value = false
}
</script>

<style scoped>
.gauge {
  width: 100%;
  max-width: 320px;
  cursor: pointer;
  touch-action: none;
}
.value-text {
  font-size: 20px;
  font-weight: 700;
  fill: #111827;
}
</style>