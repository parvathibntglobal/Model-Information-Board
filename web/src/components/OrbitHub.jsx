/**
 * OrbitHub — the sign-in page's focal object.
 *
 * A verified core with model providers orbiting it. The ring rotates and each
 * node counter-rotates at the same rate, so the glyphs stay upright while the
 * constellation turns. Two pulses travel the ring to suggest traffic without
 * needing a legend.
 *
 * The marks are abstract on purpose. Real provider logos on a sign-in screen
 * would imply partnerships that do not exist, so these are neutral glyphs
 * naming the real parts of the system: the registry, the three harvest
 * sources, the evidence, and the cells it becomes.
 */

const g = {
  width: 17, height: 17, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 1.5, strokeLinecap: 'round', strokeLinejoin: 'round',
}

const NODES = [
  { name: 'Registry',  glyph: <svg {...g}><path d="M12 3.5 20 8v8l-8 4.5L4 16V8l8-4.5Z" /></svg> },
  { name: 'GitHub',    glyph: <svg {...g}><circle cx="12" cy="12" r="8" /><path d="M12 6.5 16 15H8l4-8.5Z" /></svg> },
  { name: 'Blogs',     glyph: <svg {...g}><rect x="4.5" y="4.5" width="15" height="15" rx="2" /><rect x="9" y="9" width="6" height="6" rx="1" /></svg> },
  { name: 'Reddit',    glyph: <svg {...g}><circle cx="12" cy="12" r="3" /><ellipse cx="12" cy="12" rx="8.5" ry="4" transform="rotate(-25 12 12)" /></svg> },
  { name: 'Sources',   glyph: <svg {...g}><circle cx="7" cy="7" r="2.5" /><circle cx="17" cy="7" r="2.5" /><circle cx="12" cy="17" r="2.5" /><path d="M8.6 9 11 14.6M15.4 9 13 14.6M9.5 7h5" /></svg> },
  { name: 'Evidence',  glyph: <svg {...g}><path d="M5 6h9M5 10h14M5 14h11M5 18h7" /></svg> },
]

export default function OrbitHub() {
  const R = 37   // orbit radius, % of the box

  return (
    <div className="orbit" role="img" aria-label="Model providers orbiting a verified evidence core">
      <svg className="orbit-rings" viewBox="0 0 200 200" aria-hidden="true">
        <defs>
          <path id="orbitPath" d="M100,26 a74,74 0 1,1 -0.1,0" fill="none" />
          <radialGradient id="orbitGlow">
            <stop offset="0%" stopColor="#fff" stopOpacity=".16" />
            <stop offset="100%" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
        </defs>

        <circle cx="100" cy="100" r="62" fill="url(#orbitGlow)" />
        <circle cx="100" cy="100" r="74" className="orbit-ring" />
        <circle cx="100" cy="100" r="52" className="orbit-ring orbit-ring-inner" />

        {/* traffic on the ring */}
        <circle r="2.1" className="orbit-pulse">
          <animateMotion dur="9s" repeatCount="indefinite"><mpath href="#orbitPath" /></animateMotion>
        </circle>
        <circle r="1.6" className="orbit-pulse orbit-pulse-b">
          <animateMotion dur="9s" begin="-5.2s" repeatCount="indefinite"><mpath href="#orbitPath" /></animateMotion>
        </circle>
      </svg>

      <div className="orbit-spin">
        {NODES.map((n, i) => {
          const a = (i / NODES.length) * Math.PI * 2 - Math.PI / 2
          return (
            <span
              key={n.name}
              className="orbit-node"
              style={{
                left: `${50 + Math.cos(a) * R}%`,
                top: `${50 + Math.sin(a) * R}%`,
                animationDelay: `${i * -1.6}s`,
              }}
              title={n.name}
            >
              <span className="orbit-node-in">{n.glyph}</span>
            </span>
          )
        })}
      </div>

      <div className="orbit-core">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4.8 12.4 9.8 17.4 19.4 6.8" stroke="currentColor" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  )
}
