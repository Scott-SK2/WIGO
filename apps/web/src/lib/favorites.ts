"use client";

/** RET-01 : favoris locaux sans compte, stockés sur l'appareil (localStorage). */
const KEY = "wigo:favorites:v1";
const EVENT = "wigo:favorites-changed";

export function readFavorites(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function writeFavorites(slugs: string[]): void {
  window.localStorage.setItem(KEY, JSON.stringify(Array.from(new Set(slugs)).slice(0, 500)));
  window.dispatchEvent(new Event(EVENT));
}

export function toggleFavorite(slug: string): boolean {
  const current = readFavorites();
  const has = current.includes(slug);
  writeFavorites(has ? current.filter((s) => s !== slug) : [...current, slug]);
  return !has;
}

export function subscribeFavorites(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}
