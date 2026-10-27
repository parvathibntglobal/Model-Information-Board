/**
 * WHETHER KITE PULSE CAN BE OPENED (2026-10-23).
 *
 * Off while its team works on what is inside. While false, the admin's Kite
 * Pulse card reads "In progress" and does nothing, `/admin?p=kite-pulse` and
 * `?s=kite-pulse` fall back to the Projects list, and `/kite-pulse/*`
 * redirects to `/admin`. Turning it back on is this one line.
 */
export const KITE_PULSE_OPEN = true
