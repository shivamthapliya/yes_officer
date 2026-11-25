import { useEffect, useRef } from 'react'

// A drawer's worth of index cards drifting through the cabinet-blue panel.
// three.js is loaded on demand so it never weighs on the signed-in app bundle.

const CABINET = 0x1f3a5f
const TABS = ['#ffd84d', '#93c4ea', '#ffa3c4', '#86dbab', '#ffb784', '#cbb9ff']
const CARD_COUNT = 42
const CARD_W = 1.6
const CARD_H = 1

function drawCard(tab, seed) {
  const c = document.createElement('canvas')
  c.width = 320
  c.height = 200
  const g = c.getContext('2d')
  g.fillStyle = '#fcfcfa'
  g.fillRect(0, 0, 320, 200)
  // pale-blue ruling
  g.fillStyle = '#c4dbef'
  for (let y = 62; y < 200; y += 22) g.fillRect(0, y, 320, 2)
  // red header rule
  g.fillStyle = '#c8102e'
  g.fillRect(0, 40, 320, 4)
  // coloured card-pack tab
  g.fillStyle = tab
  g.fillRect(16, 10, 40, 18)
  // a call number and a few lines of "writing"
  g.fillStyle = 'rgba(20, 34, 58, 0.55)'
  g.fillRect(70, 15, 54, 8)
  const rand = mulberry(seed)
  for (let row = 0; row < 3; row += 1) {
    const w = 120 + rand() * 150
    g.fillStyle = `rgba(20, 34, 58, ${row === 0 ? 0.7 : 0.35})`
    g.fillRect(18, 66 + row * 44, w, row === 0 ? 11 : 8)
  }
  return c
}

function mulberry(a) {
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const easeOutExpo = (t) => (t >= 1 ? 1 : 1 - 2 ** (-10 * t))

export function CatalogScene({ className }) {
  const hostRef = useRef(null)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return undefined
    let disposed = false
    let cleanup = () => {}

    import('three').then((THREE) => {
      if (disposed) return
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.setClearColor(CABINET, 1)
      renderer.outputColorSpace = THREE.SRGBColorSpace
      host.appendChild(renderer.domElement)

      const scene = new THREE.Scene()
      scene.fog = new THREE.Fog(CABINET, 4, 19)
      const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 60)
      camera.position.set(0, 0, 6)

      const geometry = new THREE.PlaneGeometry(CARD_W, CARD_H)
      const textures = TABS.map((tab, i) => {
        const t = new THREE.CanvasTexture(drawCard(tab, i + 7))
        t.colorSpace = THREE.SRGBColorSpace
        t.anisotropy = 4
        return t
      })
      const materials = textures.map((map) => new THREE.MeshBasicMaterial({ map, side: THREE.DoubleSide, fog: true }))

      const rand = mulberry(20261125)
      const cards = Array.from({ length: CARD_COUNT }, (_, i) => {
        const mesh = new THREE.Mesh(geometry, materials[i % materials.length])
        const home = new THREE.Vector3((rand() - 0.5) * 14, (rand() - 0.5) * 11, -1 - rand() * 15)
        const card = {
          mesh,
          home,
          drift: 0.12 + rand() * 0.22,
          spin: new THREE.Vector3((rand() - 0.5) * 0.25, (rand() - 0.5) * 0.35, (rand() - 0.5) * 0.15),
          rot: new THREE.Euler(rand() * Math.PI * 0.5 - 0.25, rand() * Math.PI - Math.PI / 2, rand() * 0.6 - 0.3),
          delay: rand() * 0.6,
        }
        mesh.scale.setScalar(0.85 + rand() * 0.4)
        mesh.rotation.copy(card.rot)
        scene.add(mesh)
        return card
      })

      const resize = () => {
        const { clientWidth: w, clientHeight: h } = host
        if (!w || !h) return
        renderer.setSize(w, h, false)
        camera.aspect = w / h
        camera.updateProjectionMatrix()
      }
      resize()
      const ro = new ResizeObserver(resize)
      ro.observe(host)

      const pointer = { x: 0, y: 0 }
      const onPointer = (e) => {
        const r = host.getBoundingClientRect()
        pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1
        pointer.y = ((e.clientY - r.top) / r.height) * 2 - 1
      }
      window.addEventListener('pointermove', onPointer, { passive: true })

      const ENTRANCE = 1.6
      const start = performance.now()
      let last = start
      let raf = 0
      let running = false

      const frame = (now) => {
        const dt = Math.min((now - last) / 1000, 0.05)
        last = now
        const elapsed = (now - start) / 1000

        for (const c of cards) {
          // rise slowly, wrap to the bottom once off the top
          c.home.y += c.drift * dt
          if (c.home.y > 6.5) c.home.y -= 13
          c.rot.x += c.spin.x * dt
          c.rot.y += c.spin.y * dt
          c.rot.z += c.spin.z * dt

          // entrance: fly in from deep in the drawer
          const k = easeOutExpo(Math.max(0, (elapsed - c.delay) / ENTRANCE))
          c.mesh.position.set(c.home.x, c.home.y, c.home.z - (1 - k) * 28)
          c.mesh.rotation.set(c.rot.x + (1 - k) * 2.2, c.rot.y, c.rot.z)
        }

        camera.position.x += (pointer.x * 0.9 - camera.position.x) * 0.04
        camera.position.y += (-pointer.y * 0.6 - camera.position.y) * 0.04
        camera.lookAt(0, 0, -6)
        renderer.render(scene, camera)
        if (running) raf = requestAnimationFrame(frame)
      }

      const play = () => {
        if (running || reduced || disposed) return
        running = true
        last = performance.now()
        raf = requestAnimationFrame(frame)
      }
      const pause = () => {
        running = false
        cancelAnimationFrame(raf)
      }

      if (reduced) {
        // one still frame with every card settled
        frame(start + (ENTRANCE + 1) * 1000)
      } else {
        play()
      }

      const io = new IntersectionObserver(([entry]) => (entry.isIntersecting && !document.hidden ? play() : pause()))
      io.observe(host)
      const onVisibility = () => (document.hidden ? pause() : play())
      document.addEventListener('visibilitychange', onVisibility)

      cleanup = () => {
        pause()
        io.disconnect()
        ro.disconnect()
        document.removeEventListener('visibilitychange', onVisibility)
        window.removeEventListener('pointermove', onPointer)
        geometry.dispose()
        materials.forEach((m) => m.dispose())
        textures.forEach((t) => t.dispose())
        renderer.dispose()
        renderer.domElement.remove()
      }
    })

    return () => {
      disposed = true
      cleanup()
    }
  }, [])

  return <div ref={hostRef} className={className} aria-hidden="true" />
}
