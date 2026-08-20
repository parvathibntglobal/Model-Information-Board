import { useEffect, useRef } from 'react'

/**
 * LiquidBar — the progress bar IS the vessel.
 *
 * What makes it read as liquid rather than as a textured bar is that it knows
 * how fast it is filling. Fill rate is measured from the progress prop each
 * frame and drives everything that should answer to flow:
 *
 *   - wave amplitude at the surface, so it sloshes when pushed
 *   - forward lean, the top of the surface leading the bottom
 *   - spray, droplets thrown ahead of the front and reabsorbed
 *   - ripples running backward from the surface into the body
 *
 * Sitting still it settles; racing to 100% at the end it surges. Everything
 * else — caustics, bubbles, the meniscus — exists to keep the volume reading
 * as translucent, so you always see the vessel through it.
 *
 * Pill shape and clipping are CSS (`.lbar`); the shader only handles fluid.
 */

const VERT = `
attribute vec2 a_pos;
void main(){ gl_Position = vec4(a_pos, 0.0, 1.0); }
`

const FRAG = `
precision highp float;

uniform vec2  u_res;
uniform float u_time;
uniform float u_prog;   // 0..1 fill level
uniform float u_flow;   // 0..1 smoothed fill velocity
uniform float u_fade;

float hash(float n){ return fract(sin(n * 127.1) * 43758.5453); }

// branching veins of light through moving water
float caustics(vec2 p, float t){
  vec2 i = p;
  float c = 0.0;
  for (int n = 0; n < 4; n++){
    float tt = t * (1.0 - (3.5 / (float(n) + 1.0)));
    i = p + vec2(cos(tt - i.x) + sin(tt + i.y),
                 sin(tt - i.y) + cos(tt + i.x));
    c += 1.0 / length(vec2(p.x / (sin(i.x + tt) / 0.055),
                           p.y / (cos(i.y + tt) / 0.055)));
  }
  c /= 4.0;
  c = 1.17 - pow(c, 1.4);
  return clamp(pow(abs(c), 14.0), 0.0, 1.0);
}

void main(){
  vec2 uv = gl_FragCoord.xy / u_res;          // 0..1, origin bottom-left
  float aspect = u_res.x / max(u_res.y, 1.0);
  float t = u_time;

  // ---- the surface
  // amplitude answers to flow: still water is flat, driven water sloshes
  // Flow grows the long swells much more than the chop. Scaling all three
  // bands equally made the surface go angular instead of swelling.
  float amp = 1.0 + 2.4 * u_flow;
  float wave =
      0.004 * (1.0 + 3.1 * u_flow) * sin(uv.y *  6.0 + t * 1.30)
    + 0.009 * amp                  * sin(uv.y * 11.0 + t * (2.1 + 1.2 * u_flow))
    + 0.005 * (1.0 + 0.5 * u_flow) * sin(uv.y * 19.0 - t * (3.0 + 1.8 * u_flow));

  // the top of the surface leads the bottom when it is being pushed forward
  float lean = u_flow * 0.05 * (uv.y - 0.5);

  // hold the ends flat so the pill never looks torn at 0% or 100%
  float ends = smoothstep(0.0, 0.10, u_prog) * smoothstep(1.0, 0.90, u_prog);
  float front = u_prog + (wave + lean) * ends;

  float d = uv.x - front;                     // > 0 is ahead of the surface
  float inside = smoothstep(0.003, -0.003, d);

  // ---- body
  float depth  = smoothstep(front, front - 0.55, uv.x);   // fuller toward the back
  float settle = smoothstep(0.85, 0.05, uv.y);            // heavier at the bottom
  float c = caustics(vec2(uv.x * aspect * 0.85, uv.y * 2.2) * 4.0, t * 0.35);

  float body = inside * (0.12 + depth * 0.08 + settle * 0.05 + c * 0.44);

  // light entering through the surface and falling off into the volume
  body += inside * smoothstep(0.14, 0.0, -d) * 0.10;

  // ripples running back from the surface, stronger while it is driven
  float rd = max(-d, 0.0);
  body += inside * sin(rd * 55.0 - t * 6.5) * exp(-rd * 10.0) * 0.05 * (0.25 + u_flow);

  // sheen along the top of the volume
  body += inside * smoothstep(0.74, 1.0, uv.y) * 0.14;

  // Hard ceiling on the body. Without it the caustics stack into a white slab
  // and it stops reading as liquid — you must see the vessel through it.
  float a = min(body, 0.58);

  // ---- bubbles rising and drifting back through the body
  for (int i = 0; i < 9; i++){
    float fi = float(i);
    float s = hash(fi + 1.0);
    float bx = fract(s * 6.7 - t * (0.030 + 0.045 * s)) * max(front, 0.001);
    float by = fract(s * 3.1 + t * (0.055 + 0.070 * s));
    float r  = 0.004 + 0.011 * s;
    vec2 bd = (uv - vec2(bx, by)) * vec2(1.0, 1.0 / aspect);
    a += inside * smoothstep(r, r * 0.35, length(bd)) * (0.22 + 0.30 * s);
  }

  // ---- spray: droplets thrown ahead of the surface, only while flowing
  for (int i = 0; i < 5; i++){
    float fi = float(i);
    float s = hash(fi + 31.0);
    float life = fract(t * (0.34 + 0.40 * s) + s * 7.3);
    float dx = front + life * 0.085 * (0.5 + u_flow);
    float dy = 0.5 + (s - 0.5) * 0.62 + sin(life * 3.14159) * 0.07;
    float r  = (0.0035 + 0.0045 * s) * (1.0 - life);
    vec2 sd = (uv - vec2(dx, dy)) * vec2(1.0, 1.0 / aspect);
    a += smoothstep(r, r * 0.3, length(sd)) * 0.55 * (1.0 - life) * ends * u_flow;
  }

  // ---- meniscus: bright line, with a darker trough just behind it
  float edge = smoothstep(0.024, 0.0, abs(d));
  a += edge * 0.82 * ends;
  a -= smoothstep(0.055, 0.020, -d) * 0.13 * ends;

  // wet film just ahead of the surface
  a += smoothstep(0.075, 0.0, max(d, 0.0)) * 0.09 * ends;

  gl_FragColor = vec4(vec3(1.0), clamp(a, 0.0, 1.0) * u_fade);
}
`

function compile(gl, type, src) {
  const sh = gl.createShader(type)
  gl.shaderSource(sh, src)
  gl.compileShader(sh)
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    console.warn('[LiquidBar]', gl.getShaderInfoLog(sh))
    gl.deleteShader(sh)
    return null
  }
  return sh
}

export default function LiquidBar({ progress = 0, fade = 1 }) {
  const ref = useRef(null)
  const live = useRef({ progress, fade })
  live.current = { progress, fade }

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return

    const gl =
      canvas.getContext('webgl2', { alpha: true, antialias: false, premultipliedAlpha: false }) ||
      canvas.getContext('webgl', { alpha: true, antialias: false, premultipliedAlpha: false })
    if (!gl) return

    const vs = compile(gl, gl.VERTEX_SHADER, VERT)
    const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG)
    if (!vs || !fs) return

    const prog = gl.createProgram()
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog)
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.warn('[LiquidBar]', gl.getProgramInfoLog(prog))
      return
    }
    gl.useProgram(prog)

    const buf = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buf)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
    const loc = gl.getAttribLocation(prog, 'a_pos')
    gl.enableVertexAttribArray(loc)
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)

    const U = {
      res: gl.getUniformLocation(prog, 'u_res'),
      time: gl.getUniformLocation(prog, 'u_time'),
      prog: gl.getUniformLocation(prog, 'u_prog'),
      flow: gl.getUniformLocation(prog, 'u_flow'),
      fade: gl.getUniformLocation(prog, 'u_fade'),
    }

    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let w = 0, h = 0

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const r = canvas.getBoundingClientRect()
      const nw = Math.max(1, Math.round(r.width * dpr))
      const nh = Math.max(1, Math.round(r.height * dpr))
      if (nw === w && nh === h) return
      w = nw; h = nh
      canvas.width = w; canvas.height = h
      gl.viewport(0, 0, w, h)
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    let raf = 0
    let last = performance.now()
    const start = last
    let prev = live.current.progress
    let flow = 0

    function frame(now) {
      raf = requestAnimationFrame(frame)
      const dt = Math.min((now - last) / 1000, 1 / 30)
      last = now
      const elapsed = (now - start) / 1000
      const { progress: p, fade: f } = live.current

      // Fill rate in progress-units per second, normalised and smoothed.
      // Fast attack so a surge registers at once, slow release so the surface
      // keeps moving for a moment after the push stops.
      const rate = (p - prev) / Math.max(dt, 1e-4)
      prev = p
      const target = Math.min(1, Math.max(0, rate / 0.6))
      flow += (target - flow) * (target > flow ? 0.30 : 0.035)

      gl.uniform2f(U.res, w, h)
      gl.uniform1f(U.time, reduced ? 2.4 : elapsed)
      gl.uniform1f(U.prog, p)
      gl.uniform1f(U.flow, reduced ? 0 : flow)
      gl.uniform1f(U.fade, f)

      gl.clearColor(0, 0, 0, 0)
      gl.clear(gl.COLOR_BUFFER_BIT)
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }
    raf = requestAnimationFrame(frame)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      gl.deleteProgram(prog); gl.deleteShader(vs); gl.deleteShader(fs); gl.deleteBuffer(buf)
    }
  }, [])

  return <canvas ref={ref} className="lbar-canvas" aria-hidden="true" />
}
