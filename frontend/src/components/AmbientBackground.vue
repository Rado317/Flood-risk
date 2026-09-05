<template>
  <canvas ref="canvasRef" class="ambient-canvas" :style="{ background: bgWash }"></canvas>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  couleur: { type: String, default: '#0ea5e9' },
  theme: { type: String, default: 'light' },
})

const canvasRef = ref(null)
let renderer, scene, camera, particles, animationId, onResize

function hexToThreeColor(hex) {
  return new THREE.Color(hex)
}

// léger fond radial derrière les particules, cohérent avec le thème
const bgWash = computed(() =>
  props.theme === 'dark'
    ? 'radial-gradient(circle at 50% 20%, rgba(15, 23, 42, 0.6), rgba(2, 6, 23, 0.9) 70%)'
    : 'transparent'
)

function paramsForTheme() {
  return props.theme === 'dark'
    ? { size: 0.06, opacity: 0.55 }
    : { size: 0.05, opacity: 0.35 }
}

onMounted(() => {
  const canvas = canvasRef.value
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100)
  camera.position.z = 8

  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  const geometry = new THREE.BufferGeometry()
  const count = 180
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count * 3; i++) positions[i] = (Math.random() - 0.5) * 30
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

  const { size, opacity } = paramsForTheme()
  const material = new THREE.PointsMaterial({
    color: hexToThreeColor(props.couleur),
    size,
    transparent: true,
    opacity,
  })
  particles = new THREE.Points(geometry, material)
  scene.add(particles)

  let mouseX = 0
  function onMouseMove(event) {
    mouseX = (event.clientX / window.innerWidth - 0.5) * 0.4
  }
  window.addEventListener('mousemove', onMouseMove)

  function animate() {
    particles.rotation.y += 0.0006
    particles.rotation.x += 0.0002
    camera.position.x += (mouseX - camera.position.x) * 0.02
    camera.lookAt(0, 0, 0)
    renderer.render(scene, camera)
    animationId = requestAnimationFrame(animate)
  }
  animate()

  onResize = () => {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
  }
  window.addEventListener('resize', onResize)

  canvas._cleanup = () => window.removeEventListener('mousemove', onMouseMove)
})

watch(
  () => props.couleur,
  (nouvelle) => {
    if (particles) {
      particles.material.color = hexToThreeColor(nouvelle)
    }
  }
)

watch(
  () => props.theme,
  () => {
    if (particles) {
      const { size, opacity } = paramsForTheme()
      particles.material.size = size
      particles.material.opacity = opacity
      particles.material.needsUpdate = true
    }
  }
)

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  canvasRef.value?._cleanup?.()
  renderer?.dispose()
})
</script>

<style scoped>
.ambient-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  transition: background 0.4s ease;
}
</style>