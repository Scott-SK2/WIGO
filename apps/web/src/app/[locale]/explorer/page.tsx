import type { SearchParams } from "@wigo/shared";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Suspense } from "react";

import { EmptyState } from "@/components/EmptyState";
import { EventGrid } from "@/components/EventCard";
import { ExploreFilters } from "@/components/ExploreFilters";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const ALLOWED: (keyof SearchParams)[] = ["q", "area", "date", "date_from", "date_to", "after", "category", "free", "paid", "max_price", "lang", "format", "include_online", "accessible", "family", "lat", "lon", "radius_km", "sort", "cursor", "page_size"];

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("explore");
  return { title: t("title") };
}

/** SCR-02 : Explorer — recherche, filtres combinables, tri, pagination par curseur, états vides. */
export default async function ExplorePage({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const raw = await searchParams;
  const query: SearchParams = {};
  for (const k of ALLOWED) {
    const v = raw[k];
    if (typeof v === "string" && v) (query as Record<string, string>)[k] = v;
  }
  const [t, page, categories, areas, counts] = await Promise.all([getTranslations("explore"), api.events(query), api.categories(), api.areas(), api.counts()]);
  const nextCursor = page.next ? new URL(page.next).searchParams.get("cursor") : null;
  const hasFilters = Object.keys(query).some((k) => k !== "cursor" && k !== "page_size");

  return (
    <div className="container-wigo py-8">
      <h1 className="section-title">{t("title")}</h1>
      <div className="mt-5">
        <Suspense fallback={null}>
          <ExploreFilters categories={categories} areas={areas} counts={counts} />
        </Suspense>
      </div>
      <p className="mt-6 text-sm text-gris" aria-live="polite">{t("results", { count: page.results.length })}{page.next ? "+" : ""}</p>
      <div className="mt-4">
        {page.results.length ? (
          <EventGrid events={page.results} />
        ) : (
          <EmptyState title={t("emptyTitle")} text={t("emptyText")}>
            <Link href={{ pathname: "/explorer", query: { date: "weekend" } }} className="chip">{t("emptyWeekend")}</Link>
            {hasFilters && <Link href="/explorer" className="chip">{t("emptyAll")}</Link>}
            {query.category && <Link href={{ pathname: "/explorer", query: withoutCategory(query) }} className="chip">{t("emptyAllCategories")}</Link>}
          </EmptyState>
        )}
      </div>
      {nextCursor && (
        <div className="mt-10 flex justify-center">
          <Link href={{ pathname: "/explorer", query: { ...(query as Record<string, string>), cursor: nextCursor } }} className="btn-outline" rel="next">{t("loadMore")}</Link>
        </div>
      )}
    </div>
  );
}

function withoutCategory(query: SearchParams): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(query)) if (k !== "category" && typeof v === "string") out[k] = v;
  return out;
}
