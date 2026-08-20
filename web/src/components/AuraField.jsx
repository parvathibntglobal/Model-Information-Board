import { useEffect, useRef } from 'react'

/**
 * AuraField — the atmospheric layer behind the sign-in page.
 *
 * Soft volumetric pools of light drifting over a dark ground, with a standing
 * glow behind the orbit so the centre of the composition reads as the source.
 * Monochrome, low contrast, and deliberately slow: it is a backdrop, and if you
 * notice it working it is too strong.
 */

const VERT = `
attribute vec2 a_pos;
void main(){ gl_Position = vec4(a_pos, 0.0, 1.0); }
`

const FRAG = `
precision highp float;

uniform vec2  u_res;
uniform float u_time;
uniform float u_fade;

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 4; i++){ v += a * noise(p); p *= 2.03; a *= 0.5; }
  return v;
}

void main(){
  vec2 uv = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y;
  float t = u_time * 0.045;

  // standing glow behind the orbit — the source of the composition
  float core = exp(-dot(uv, uv) * 3.1) * 0.30;

  // drifting pools, warped so they fold rather than slide
  vec2 q = uv * 1.5 + vec2(t, -t * 0.7);
  q += 0.42 * vec2(fbm(q + t), fbm(q.yx - t * 0.8));
  float pools = fbm(q) * fbm(q * 0.6 + 3.7);
  pools = smoothstep(0.10, 0.62, pools) * 0.20;

  // a slow sweep of light across the field
  float sweep = smoothstep(0.55, 0.0, abs(uv.x - sin(u_time * 0.07) * 0.55)) * 0.05;

  // hold it away from the page edges
  float vig = smoothstep(1.15, 0.10, length(uv * vec2(0.72, 1.0)));

  float a = (core + pools + sweep) * vig;

  // fine grain stops the gradients banding on dark panels
  a += (hash(gl_FragCoord.xy + fract(u_time)) - 0.5) * 0.012;

  gl_FragColor = vec4(vec3(1.0), clamp(a, 0.0, 1.0) * u_fade);
}
`

function compile(gl, type, src) {
  const sh = gl.createShader(type)
  gl.shaderSource(sh, src)
  gl.compileShader(sh)
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    console.warn('[AuraField]', gl.getShaderInfoLog(sh))
    gl.deleteShader(sh)
    return null
  }
  return sh
}

export default function AuraField() {
  const ref = useRef(null)

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
      console.warn('[AuraField]', gl.getProgramInfoLog(prog))
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
      fade: gl.getUniformLocation(prog, 'u_fade'),
    }

    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let w = 0, h = 0

    function resize() {
      // half-res: it is all low-frequency, nobody can tell, and it costs a third
      const dpr = Math.min(window.devicePixelRatio || 1, 2) * 0.6
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
    let fade = 0
    const start = performance.now()

    function frame(now) {
      raf = requestAnimationFrame(frame)
      const elapsed = (now - start) / 1000
      fade = Math.min(1, elapsed / 1.2)

      gl.uniform2f(U.res, w, h)
      gl.uniform1f(U.time, reduced ? 8.0 : elapsed)
      gl.uniform1f(U.fade, fade)

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

  return <canvas ref={ref} className="aura" aria-hidden="true" />
}
