/* Inline icons — no icon dependency, all stroke-based on currentColor. */

const base = {
  width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round',
  'aria-hidden': true,
}

export const IconQuote = (p) => (
  <svg {...base} {...p}>
    <path d="M9 7H5.5A1.5 1.5 0 0 0 4 8.5v3A1.5 1.5 0 0 0 5.5 13H8v1.5A2.5 2.5 0 0 1 5.5 17" />
    <path d="M19 7h-3.5A1.5 1.5 0 0 0 14 8.5v3a1.5 1.5 0 0 0 1.5 1.5H18v1.5a2.5 2.5 0 0 1-2.5 2.5" />
  </svg>
)

export const IconPeople = (p) => (
  <svg {...base} {...p}>
    <path d="M15.5 20v-1.6a3.4 3.4 0 0 0-3.4-3.4H6.9A3.4 3.4 0 0 0 3.5 18.4V20" />
    <circle cx="9.5" cy="8" r="3.2" />
    <path d="M20.5 20v-1.6a3.4 3.4 0 0 0-2.6-3.3M16 5a3.2 3.2 0 0 1 0 6.2" />
  </svg>
)

export const IconSplit = (p) => (
  <svg {...base} {...p}>
    <path d="M4 6h4l4 6 4 6h4" />
    <path d="M4 18h4l3-4.5" />
    <path d="M17 3l3 3-3 3M17 15l3 3-3 3" />
  </svg>
)

export const IconSilence = (p) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M8.5 12h7" />
  </svg>
)

export const IconArrow = (p) => (
  <svg {...base} {...p}>
    <path d="M5 12h13M13 6l6 6-6 6" />
  </svg>
)

export const IconSearch = (p) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M16 16l4 4" />
  </svg>
)

export const IconAlert = (p) => (
  <svg {...base} {...p}>
    <path d="M12 4.5 3 19.5h18L12 4.5Z" />
    <path d="M12 10v4M12 17h.01" />
  </svg>
)

export const IconCheck = (p) => (
  <svg {...base} {...p}>
    <path d="M4.5 12.5 9.5 17.5 19.5 7" />
  </svg>
)

export const IconExternal = (p) => (
  <svg {...base} {...p}>
    <path d="M14 4h6v6M20 4l-8.5 8.5" />
    <path d="M18 14v4.5A1.5 1.5 0 0 1 16.5 20h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10" />
  </svg>
)

export const IconLayers = (p) => (
  <svg {...base} {...p}>
    <path d="M12 3 3 7.5 12 12l9-4.5L12 3Z" />
    <path d="m3 12.5 9 4.5 9-4.5M3 17l9 4.5 9-4.5" />
  </svg>
)

export const IconGauge = (p) => (
  <svg {...base} {...p}>
    <path d="M4 18a8 8 0 1 1 16 0" />
    <path d="m12 14 4-4" />
  </svg>
)

export const IconFilter = (p) => (
  <svg {...base} {...p}>
    <path d="M4 5h16l-6.2 7.4V19l-3.6 2v-8.6L4 5Z" />
  </svg>
)
