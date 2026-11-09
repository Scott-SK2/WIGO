import type { EventCard } from "@wigo/shared";

const TZ = "Europe/Brussels";

export function formatDateTime(iso: string | null | undefined, locale: string, opts?: Intl.DateTimeFormatOptions): string {
  if (!iso) return "";
  return new Intl.DateTimeFormat(locale, {
    timeZone: TZ,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    ...opts,
  }).format(new Date(iso));
}

export function formatDay(iso: string | null | undefined, locale: string): string {
  if (!iso) return "";
  return new Intl.DateTimeFormat(locale, { timeZone: TZ, weekday: "long", day: "numeric", month: "long" }).format(new Date(iso));
}

export function formatTime(iso: string | null | undefined, locale: string): string {
  if (!iso) return "";
  return new Intl.DateTimeFormat(locale, { timeZone: TZ, hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

export function formatPrice(pricing: EventCard["pricing"], locale: string, labels: { free: string; pwyw: string; from: string }): string {
  if (pricing.type === "FREE") return labels.free;
  if (pricing.type === "PWYW") return labels.pwyw;
  const fmt = new Intl.NumberFormat(locale, { style: "currency", currency: pricing.currency || "EUR", maximumFractionDigits: 0 });
  const min = pricing.min != null ? Number(pricing.min) : null;
  const max = pricing.max != null ? Number(pricing.max) : null;
  if (min != null && max != null && max !== min) return `${fmt.format(min)} – ${fmt.format(max)}`;
  if (min != null) return fmt.format(min);
  return pricing.details || "";
}

export function localized(names: Record<string, string> | undefined, locale: string): string {
  if (!names) return "";
  return names[locale] ?? names.fr ?? Object.values(names)[0] ?? "";
}

/** Dégradé de carte déterministe à partir du slug (§7.3 : deux couleurs de la palette). */
export function cardGradient(seed: string): string {
  const palette = [
    ["#A2694F", "#4F2F23"],
    ["#2F4C7A", "#1B1A22"],
    ["#7A4A36", "#2F4C7A"],
    ["#E2B33C", "#A2694F"],
    ["#4F2F23", "#2F4C7A"],
    ["#A2694F", "#E3CDB9"],
  ];
  let h = 0;
  for (const c of seed) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const [a, b] = palette[h % palette.length];
  return `linear-gradient(${135 + (h % 60)}deg, ${a}, ${b})`;
}
