/**
 * Types partagés WIGO. `api.d.ts` est généré depuis l'OpenAPI de l'API Django (`pnpm gen:api`).
 * Les alias ci-dessous exposent les schémas les plus utilisés par le web et le mobile.
 */
import type { components, paths } from "./api";

export type Schemas = components["schemas"];
export type Paths = paths;

export type EventCard = Schemas["EventCard"];
export type EventDetail = Schemas["EventDetail"];
export type Category = Schemas["Category"];
export type Area = Schemas["Area"];
export type Venue = Schemas["Venue"];
export type OrganizationPublic = Schemas["OrganizationPublic"];
export type Me = Schemas["Me"];

export type Locale = "fr" | "nl" | "en";
export const LOCALES: Locale[] = ["fr", "nl", "en"];
export const DEFAULT_LOCALE: Locale = "fr";

export type EventStatus =
  | "DRAFT"
  | "PENDING_REVIEW"
  | "CHANGES_REQUESTED"
  | "REJECTED"
  | "PUBLISHED"
  | "CANCELLED"
  | "ARCHIVED";

export interface Paginated<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Paramètres de recherche documentés dans le cahier des charges §9.2. */
export interface SearchParams {
  q?: string;
  area?: string;
  date?: "today" | "tomorrow" | "weekend" | string;
  date_from?: string;
  date_to?: string;
  after?: string;
  category?: string;
  free?: "1";
  paid?: "1";
  max_price?: string;
  lang?: Locale;
  format?: "ONSITE" | "ONLINE" | "HYBRID";
  include_online?: "1";
  accessible?: "1";
  family?: "1";
  lat?: string;
  lon?: string;
  radius_km?: string;
  sort?: "relevance" | "date" | "distance";
  cursor?: string;
  page_size?: string;
}

/** Jetons de couleur du design system WIGO (§7.1). */
export const COLORS = {
  brique: "#A2694F",
  briqueFonce: "#7A4A36",
  briqueProfond: "#4F2F23",
  sable: "#E3CDB9",
  creme: "#F6EDE4",
  papier: "#FCF8F4",
  encre: "#1B1A22",
  bleuNuit: "#2F4C7A",
  or: "#E2B33C",
  grisTexte: "#756963",
} as const;
