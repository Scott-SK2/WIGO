import "server-only";

import type { Area, Category, EventCard, EventDetail, OrganizationPublic, Paginated, SearchParams } from "@wigo/shared";

/** URL de l'API vue depuis le serveur Next (SSR). Côté navigateur, utiliser NEXT_PUBLIC_API_URL. */
const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function get<T>(path: string, init?: RequestInit & { revalidate?: number }): Promise<T> {
  const res = await fetch(`${API_URL}/api/v1${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
    next: { revalidate: init?.revalidate ?? 60 },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      message = (await res.json())?.error?.message ?? message;
    } catch {
      /* corps non JSON */
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

/** Variante tolérante : renvoie `fallback` si l'API est indisponible (build, panne). */
async function safe<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) throw error;
    console.error("[wigo] API indisponible :", error instanceof Error ? error.message : error);
    return fallback;
  }
}

export function toQuery(params: SearchParams | Record<string, string | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) sp.set(k, String(v));
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export interface HomePayload {
  tonight: EventCard[];
  weekend: EventCard[];
  free: EventCard[];
  selection: EventCard[];
  ongoing: EventCard[];
  counts: { active_events: number; today: number };
}

const EMPTY_HOME: HomePayload = { tonight: [], weekend: [], free: [], selection: [], ongoing: [], counts: { active_events: 0, today: 0 } };
const EMPTY_PAGE = { next: null, previous: null, results: [] };

export const api = {
  home: () => safe(get<HomePayload>("/home", { revalidate: 120 }), EMPTY_HOME),
  events: (params: SearchParams) => safe(get<Paginated<EventCard>>(`/events${toQuery(params)}`, { revalidate: 60 }), EMPTY_PAGE),
  event: (slug: string) => get<EventDetail>(`/events/${encodeURIComponent(slug)}`, { revalidate: 60 }),
  categories: () => safe(get<Category[]>("/categories", { revalidate: 3600 }), []),
  areas: () => safe(get<Area[]>("/areas", { revalidate: 3600 }), []),
  counts: () => safe(get<Record<string, number>>("/events/counts", { revalidate: 300 }), {}),
  organization: (slug: string) => get<OrganizationPublic>(`/organizations/${encodeURIComponent(slug)}`, { revalidate: 300 }),
};

export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
