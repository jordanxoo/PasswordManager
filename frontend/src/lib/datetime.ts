/** Date helpers for timestamps coming from the API.
 *
 *  The backend now emits UTC with an explicit offset ('Z'), so a plain
 *  `new Date()` is correct. `parseServerDate` stays defensive: if a value ever
 *  arrives without a timezone, it's assumed to be UTC (which is how the app
 *  stores timestamps) rather than being reinterpreted as local time. */
export function parseServerDate(iso: string): Date {
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso);
  return new Date(hasTz ? iso : `${iso}Z`);
}

/** Compact "x ago" label, e.g. "just now", "5 min ago", "3 days ago". */
export function relativeTime(iso: string): string {
  const sec = Math.round((Date.now() - parseServerDate(iso).getTime()) / 1000);
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  const day = Math.round(hr / 24);
  if (day < 30) return `${day} day${day > 1 ? "s" : ""} ago`;
  const mo = Math.round(day / 30);
  if (mo < 12) return `${mo} mo ago`;
  return `${Math.round(mo / 12)} yr ago`;
}

/** Absolute local-time string for tooltips. */
export function formatDateTime(iso: string): string {
  return parseServerDate(iso).toLocaleString();
}
