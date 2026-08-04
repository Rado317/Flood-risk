<template>
  <div class="welcome" @click.self="enter">
    <canvas ref="canvasRef"></canvas>
    <div class="overlay">
      <h1 class="logo">ARO<span class="dot">.ai</span></h1>
      <p class="tagline">Surveillance intelligente du risque d'inondation</p>
      <p class="sub">Station Ambohimanambola — Madagascar</p>
      <button class="enter-btn" @click="enter">Entrer</button>
    </div>
    <div class="scroll-hint">cliquez n'importe où pour continuer</div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as THREE from 'three'

const emit = defineEmits(['enter'])
const canvasRef = ref(null)
let renderer, scene, camera, animationId, onResize

function enter() {
  emit('enter')
}

onMounted(() => {
  const canvas = canvasRef.value
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100)
  camera.position.z = 6

  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  const outerGeometry = new THREE.IcosahedronGeometry(2, 1)
  const outerMaterial = new THREE.MeshBasicMaterial({
    color: 0x38bdf8,
    wireframe: true,
    transparent: true,
    opacity: 0.85,
  })
  const outerMesh = new THREE.Mesh(outerGeometry, outerMaterial)
  scene.add(outerMesh)

  const innerGeometry = new THREE.IcosahedronGeometry(1.3, 1)
  const innerMaterial = new THREE.MeshBasicMaterial({
    color: 0x0ea5e9,
    wireframe: true,
    transparent: true,
    opacity: 0.45,
  })
  const innerMesh = new THREE.Mesh(innerGeometry, innerMaterial)
  scene.add(innerMesh)

  const particlesGeometry = new THREE.BufferGeometry()
  const count = 350
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count * 3; i++) positions[i] = (Math.random() - 0.5) * 22
  particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const particlesMaterial = new THREE.PointsMaterial({ color: 0x7dd3fc, size: 0.03 })
  const particles = new THREE.Points(particlesGeometry, particlesMaterial)
  scene.add(particles)

  let mouseX = 0
  let mouseY = 0
  function onMouseMove(event) {
    mouseX = (event.clientX / window.innerWidth - 0.5) * 0.6
    mouseY = (event.clientY / window.innerHeight - 0.5) * 0.6
  }
  window.addEventListener('mousemove', onMouseMove)

  function animate() {
    outerMesh.rotation.x += 0.0025
    outerMesh.rotation.y += 0.0035
    innerMesh.rotation.x -= 0.0018
    innerMesh.rotation.y -= 0.0022
    particles.rotation.y += 0.0004

    camera.position.x += (mouseX - camera.position.x) * 0.03
    camera.position.y += (-mouseY - camera.position.y) * 0.03
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

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  canvasRef.value?._cleanup?.()
  renderer?.dispose()
})
</script>

<style scoped>
.welcome {
  position: fixed;
  inset: 0;
  background: radial-gradient(circle at 50% 30%, #0f172a, #020617 70%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
  z-index: 50;
}
canvas {
  position: absolute;
  inset: 0;
}
.overlay {
  position: relative;
  text-align: center;
  color: white;
  font-family: system-ui, sans-serif;
  pointer-events: none;
  animation: fadeIn 1.2s ease;
}
.logo {
  font-size: 64px;
  font-weight: 800;
  letter-spacing: 3px;
  margin: 0;
}
.logo .dot {
  color: #38bdf8;
}
.tagline {
  margin-top: 10px;
  color: #cbd5e1;
  font-size: 17px;
}
.sub {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}
.enter-btn {
  margin-top: 36px;
  padding: 12px 36px;
  border-radius: 999px;
  border: 1px solid #38bdf8;
  background: transparent;
  color: #38bdf8;
  font-size: 15px;
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.25s ease;
}
.enter-btn:hover {
  background: #38bdf8;
  color: #020617;
  box-shadow: 0 0 30px rgba(56, 189, 248, 0.5);
}
.scroll-hint {
  position: absolute;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  color: #475569;
  font-size: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>