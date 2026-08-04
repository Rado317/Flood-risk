<template>
  <canvas ref="canvasRef" class="ambient-canvas"></canvas>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  couleur: { type: String, default: '#0ea5e9' },
})

const canvasRef = ref(null)
let renderer, scene, camera, particles, animationId, onResize

function hexToThreeColor(hex) {
  return new THREE.Color(hex)
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

  const material = new THREE.PointsMaterial({
    color: hexToThreeColor(props.couleur),
    size: 0.05,
    transparent: true,
    opacity: 0.35,
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
}
</style>