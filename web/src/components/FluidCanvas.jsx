import { useEffect, useRef } from 'react'

/**
 * FluidCanvas — WebGL metaball field.
 *
 * A cluster of implicit spheres drifts on lissajous paths; their scalar fields
 * sum and everything above the iso-surface is painted white.
 *
 * Three things make it read as liquid rather than as moving circles:
 *
 *  1. The cursor drags a CHAIN of balls, not one. Each link lags the one ahead
 *     of it, so fast movement pulls a tail out of the mass and slow movement
 *     lets it flow back — that lag is most of the perceived viscosity.
 *  2. Motion STRETCHES the droplets along their direction of travel, the way a
 *     real bead of water elongates when it is flung.
 *  3. Speed drives turbulence. The surface only ripples when something disturbs it.
 *
 * Double-click bursts the mass apart and lets surface tension pull it back:
 * the impulse is a damped spring that overshoots past zero, so the field
 * scatters, converges through the centre, and settles.
 *
 * The canvas composites with `mix-blend-mode: difference` (see .fluid), which
 * is what makes the mass invert the headline instead of covering it.
 *
 * No dependencies. GLSL ES 1.00, so it runs on WebGL1 as well as WebGL2.
 */

const TRAIL = 6
const BURST_LIFE = 6.0   // seconds — the rejoin is deliberately unhurried

const VERT = `
attribute vec2 a_pos;
void main(){ gl_Position = vec4(a_pos, 0.0, 1.0); }
`

const FRAG = `
precision highp float;

#define TRAIL ${TRAIL}

uniform vec2  u_res;
uniform float u_time;
uniform float u_intro;      // 0..1 entrance
uniform vec2  u_trail[TRAIL];
uniform float u_pointerOn;  // 0..1
uniform float u_speed;      // 0..1, smoothed cursor speed
uniform vec2  u_dir;        // unit vector, smoothed direction of travel
uniform float u_burst;      // ~-0.3 .. 1  (negative = drawn back inward)
uniform vec2  u_burstAt;

// isotropic metaball: r^2 / d^2
float ball(vec2 p, vec2 c, float r){
  vec2 d = p - c;
  return (r * r) / (dot(d, d) + 0.0004);
}

// stretched along 'dir' — compressing the coordinate makes the field reach further
float beadStretched(vec2 p, vec2 c, float r, vec2 dir, float stretch){
  vec2 d = p - c;
  vec2 along  = dir * dot(d, dir);
  vec2 across = d - along;
  d = along / (1.0 + stretch) + across * (1.0 + stretch * 0.30);
  return (r * r) / (dot(d, d) + 0.0004);
}

// the double-click impulse, applied to a ball centre
vec2 shove(vec2 c, float seed){
  if (abs(u_burst) < 0.001) return c;
  vec2 d = c - u_burstAt;
  float len = max(length(d), 0.0015);
  vec2 dir = d / len;
  // fan the paths apart so it scatters rather than exploding on straight lines
  float a = (seed - 0.5) * 1.5 * u_burst;
  float s = sin(a), co = cos(a);
  dir = vec2(dir.x * co - dir.y * s, dir.x * s + dir.y * co);
  // closer to the impact = shoved harder
  float push = u_burst * (0.20 + 0.16 * seed) / (0.34 + len);
  // never let the inward swing pull a ball through the origin — it gathers, it
  // does not collapse to a point, which would read as vanishing rather than merging
  push = max(push, -0.55 * len);
  return c + dir * push;
}

void main(){
  // aspect-corrected space, y in [-0.5, 0.5]
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y;

  float t = u_time;
  float burstMag = abs(u_burst);

  // turbulence rises with cursor speed and with the burst — a still surface is still
  float churn = 1.0 + 1.7 * u_speed + 1.1 * burstMag;
  p += 0.011 * churn * vec2(
    sin(p.y * 7.0 + t * (0.90 + 0.8 * u_speed)),
    cos(p.x * 7.0 - t * (0.75 + 0.8 * u_speed))
  );
  p += 0.006 * churn * vec2(
    sin(p.y * 15.0 - t * 1.35),
    cos(p.x * 13.0 + t * 1.15)
  );

  float s = u_intro;
  // the mass leans toward the cursor, so the whole body reacts and not just the tail
  vec2 lean = u_trail[0] * 0.05 * u_pointerOn;
  vec2 o = vec2(0.150 + sin(t * 0.13) * 0.035, cos(t * 0.11) * 0.022) + lean;

  // droplets shrink as they scatter and swell as they coalesce
  float vol = 1.0 - 0.26 * max(u_burst, 0.0) - 0.62 * min(u_burst, 0.0);

  float f = 0.0;
  f += ball(p, shove(o + vec2(sin(t * 0.31) * 0.085, cos(t * 0.27) * 0.062), 0.13), 0.116 * s * vol);
  f += ball(p, shove(o + vec2(cos(t * 0.23) * 0.115, sin(t * 0.35) * 0.075), 0.31), 0.100 * s * vol);
  f += ball(p, shove(o + vec2(sin(t * 0.19 + 2.1) * 0.135, cos(t * 0.29 + 1.3) * 0.090), 0.52), 0.088 * s * vol);
  f += ball(p, shove(o + vec2(cos(t * 0.37 + 0.8) * 0.100, sin(t * 0.21 + 2.7) * 0.105), 0.68), 0.077 * s * vol);
  f += ball(p, shove(o + vec2(sin(t * 0.41 + 4.2) * 0.155, cos(t * 0.17 + 3.4) * 0.058), 0.84), 0.068 * s * vol);
  f += ball(p, shove(o + vec2(cos(t * 0.15 + 1.9) * 0.070, sin(t * 0.43 + 0.4) * 0.118), 0.97), 0.062 * s * vol);

  // satellite that breaks off and rejoins — keeps it from reading as one lump
  vec2 sat = o + vec2(sin(t * 0.24 + 1.1) * 0.235, cos(t * 0.33 + 2.2) * 0.135);
  f += ball(p, shove(sat, 0.44), (0.040 + 0.010 * sin(t * 0.6)) * s * vol);

  // the cursor chain — head is largest, each link lags and thins
  float stretch = u_speed * 1.45;
  for (int i = 0; i < TRAIL; i++) {
    float k = float(i) / float(TRAIL - 1);          // 0 at the head
    float r = mix(0.088, 0.020, k) * s * u_pointerOn;
    f += beadStretched(p, u_trail[i], r, u_dir, stretch * (1.0 - 0.55 * k));
  }

  // iso-surface at 1.0, softened just enough to stay liquid rather than cut
  float e = 0.030;
  float a = smoothstep(1.0 - e, 1.0 + e, f);

  // restrained halo — enough to seat the mass, not enough to fog it
  float halo = smoothstep(0.62, 1.0, f) * 0.028;

  float alpha = clamp(a + halo, 0.0, 1.0) * u_intro;
  gl_FragColor = vec4(vec3(1.0), alpha);
}
`

function compile(gl, type, src) {
  const sh = gl.createShader(type)
  gl.shaderSource(sh, src)
  gl.compileShader(sh)
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    console.warn('[FluidCanvas]', gl.getShaderInfoLog(sh))
    gl.deleteShader(sh)
    return null
  }
  return sh
}

export default function FluidCanvas({ className = 'fluid' }) {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return

    const gl =
      canvas.getContext('webgl2', { alpha: true, antialias: false, premultipliedAlpha: false }) ||
      canvas.getContext('webgl', { alpha: true, antialias: false, premultipliedAlpha: false })

    if (!gl) return // no WebGL — the hero simply renders without the field

    const vs = compile(gl, gl.VERTEX_SHADER, VERT)
    const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG)
    if (!vs || !fs) return

    const prog = gl.createProgram()
    gl.attachShader(prog, vs)
    gl.attachShader(prog, fs)
    gl.linkProgram(prog)
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.warn('[FluidCanvas]', gl.getProgramInfoLog(prog))
      return
    }
    gl.useProgram(prog)

    // fullscreen triangle
    const buf = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buf)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
    const loc = gl.getAttribLocation(prog, 'a_pos')
    gl.enableVertexAttribArray(loc)
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)

    const U = {
      res: gl.getUniformLocation(prog, 'u_res'),
      time: gl.getUniformLocation(prog, 'u_time'),
      intro: gl.getUniformLocation(prog, 'u_intro'),
      trail: gl.getUniformLocation(prog, 'u_trail'),
      pointerOn: gl.getUniformLocation(prog, 'u_pointerOn'),
      speed: gl.getUniformLocation(prog, 'u_speed'),
      dir: gl.getUniformLocation(prog, 'u_dir'),
      burst: gl.getUniformLocation(prog, 'u_burst'),
      burstAt: gl.getUniformLocation(prog, 'u_burstAt'),
    }

    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    /* ---------------------------------------------------------- state */

    // head of the chain is a damped spring toward the cursor; the rest follow it
    const head = { x: 0.22, y: 0.06, vx: 0, vy: 0 }
    const target = { x: 0.22, y: 0.06 }
    const chain = Float32Array.from({ length: TRAIL * 2 }, (_, i) => (i % 2 ? 0.06 : 0.22))

    let on = 0, onTarget = 0
    let speed = 0
    const dir = { x: 1, y: 0 }

    // double-click impulse
    let burstAt = [0, 0]
    let burstT = -1

    let w = 0, h = 0

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const r = canvas.getBoundingClientRect()
      const nw = Math.max(1, Math.round(r.width * dpr))
      const nh = Math.max(1, Math.round(r.height * dpr))
      if (nw === w && nh === h) return
      w = nw; h = nh
      canvas.width = w
      canvas.height = h
      gl.viewport(0, 0, w, h)
    }
    resize()

    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    // the hero frame is the interaction surface; the canvas itself is inert
    const surface = canvas.closest('.hero-frame') || canvas.parentElement

    function toScene(ev) {
      const r = canvas.getBoundingClientRect()
      if (!r.height) return null
      return {
        x: (ev.clientX - r.left - r.width / 2) / r.height,
        y: -(ev.clientY - r.top - r.height / 2) / r.height,
      }
    }

    function onMove(ev) {
      const s = toScene(ev)
      if (!s) return
      target.x = s.x; target.y = s.y
      onTarget = 1
    }
    function onLeave() { onTarget = 0 }

    function onBurst(ev) {
      if (reduced) return
      const s = toScene(ev)
      if (!s) return
      burstAt = [s.x, s.y]
      burstT = 0
    }

    surface?.addEventListener('pointermove', onMove, { passive: true })
    surface?.addEventListener('pointerleave', onLeave, { passive: true })
    surface?.addEventListener('dblclick', onBurst)

    // don't burn frames while scrolled away
    let visible = true
    const io = new IntersectionObserver(
      (entries) => { visible = entries[0]?.isIntersecting ?? true },
      { threshold: 0 }
    )
    io.observe(canvas)

    let raf = 0
    let last = performance.now()
    const start = last

    function frame(now) {
      raf = requestAnimationFrame(frame)
      if (!visible) { last = now; return }

      // clamped so a background tab or a stall cannot fling the chain
      const dt = Math.min((now - last) / 1000, 1 / 30)
      last = now
      const elapsed = (now - start) / 1000

      const intro = reduced ? 1 : Math.min(1, elapsed / 1.5)
      const eased = 1 - Math.pow(1 - intro, 3)

      /* -------- head: critically damped spring, so it arrives without jitter */
      const stiff = 190, damp = 22
      const ax = (target.x - head.x) * stiff - head.vx * damp
      const ay = (target.y - head.y) * stiff - head.vy * damp
      head.vx += ax * dt
      head.vy += ay * dt
      const dx = head.vx * dt
      const dy = head.vy * dt
      head.x += dx
      head.y += dy

      /* -------- speed and direction, smoothed */
      const inst = Math.hypot(dx, dy) / Math.max(dt, 1e-4)   // scene units / second
      const normalised = Math.min(1, inst / 2.4)
      speed += (normalised - speed) * (normalised > speed ? 0.28 : 0.06) // fast attack, slow release
      if (inst > 0.02) {
        const l = Math.hypot(dx, dy) || 1
        dir.x += (dx / l - dir.x) * 0.20
        dir.y += (dy / l - dir.y) * 0.20
        const dl = Math.hypot(dir.x, dir.y) || 1
        dir.x /= dl; dir.y /= dl
      }

      /* -------- chain: each link chases the one ahead, loosening down the tail */
      chain[0] = head.x
      chain[1] = head.y
      for (let i = 1; i < TRAIL; i++) {
        const k = 0.34 - i * 0.040
        chain[i * 2]     += (chain[(i - 1) * 2]     - chain[i * 2])     * k
        chain[i * 2 + 1] += (chain[(i - 1) * 2 + 1] - chain[i * 2 + 1]) * k
      }

      on += (onTarget - on) * 0.08

      /* -------- burst.
         A single damped cosine would make the split and the rejoin the same
         speed, which is the one thing water never does. So it is two lobes with
         very different time constants:

           OUT   fast attack, then a slow viscous bleed-off   (tau 0.62s)
           IN    a broad, late swell of surface tension       (peaks at 2.2s)

         Net effect: scatters in ~0.15s, drifts apart for a second, then is
         drawn back through the centre over four or five seconds and settles. */
      let burst = 0
      if (burstT >= 0) {
        burstT += dt
        if (burstT > BURST_LIFE) {
          burstT = -1
        } else {
          const t2 = burstT
          const attack = 1 - Math.exp(-t2 / 0.06)
          const out = 1.45 * attack * Math.exp(-t2 / 0.62)

          // gamma-shaped pulse: zero at 0, peaks at 1.0, long tail
          const u = t2 / 1.6
          const pull = 0.34 * u * u * Math.exp(2 * (1 - u))

          // ease the last stretch to nothing so it never snaps off
          const fade = Math.min(1, (BURST_LIFE - t2) / 1.4)

          burst = (out - pull) * fade
        }
      }

      gl.uniform2f(U.res, w, h)
      gl.uniform1f(U.time, reduced ? 6.2 : elapsed)
      gl.uniform1f(U.intro, eased)
      gl.uniform2fv(U.trail, chain)
      gl.uniform1f(U.pointerOn, on)
      gl.uniform1f(U.speed, reduced ? 0 : speed)
      gl.uniform2f(U.dir, dir.x, dir.y)
      gl.uniform1f(U.burst, burst)
      gl.uniform2f(U.burstAt, burstAt[0], burstAt[1])

      gl.clearColor(0, 0, 0, 0)
      gl.clear(gl.COLOR_BUFFER_BIT)
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }
    raf = requestAnimationFrame(frame)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      io.disconnect()
      surface?.removeEventListener('pointermove', onMove)
      surface?.removeEventListener('pointerleave', onLeave)
      surface?.removeEventListener('dblclick', onBurst)
      gl.deleteProgram(prog)
      gl.deleteShader(vs)
      gl.deleteShader(fs)
      gl.deleteBuffer(buf)
    }
  }, [])

  return <canvas ref={ref} className={className} aria-hidden="true" />
}
