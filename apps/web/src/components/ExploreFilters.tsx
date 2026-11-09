"use client";

import type { Area, Category } from "@wigo/shared";
import clsx from "clsx";
import { useLocale, useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState, useTransition } from "react";

import { localized } from "@/lib/format";

import { Icon } from "./Icon";

/** SCR-02 : filtres combinables, URL partageable (chaque filtre est un paramètre de requête). */
export function ExploreFilters({ categories, areas, counts }: { categories: Category[]; areas: Area[]; counts: Record<string, number> }) {
  const t = useTranslations("explore");
  const locale = useLocale();
  const router = useRouter();
  const sp = useSearchParams();
  const [, startTransition] = useTransition();
  const [locating, setLocating] = useState(false);

  const set = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(sp.toString());
      next.delete("cursor");
      for (const [k, v] of Object.entries(patch)) {
        if (v) next.set(k, v);
        else next.delete(k);
      }
      startTransition(() => router.replace(`?${next.toString()}`, { scroll: false }));
    },
    [router, sp],
  );
  const toggle = (k: string) => set({ [k]: sp.get(k) ? null : "1" });
  const q = sp.get("q") ?? "";

  function nearMe() {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        set({ lat: pos.coords.latitude.toFixed(5), lon: pos.coords.longitude.toFixed(5), radius_km: sp.get("radius_km") ?? "3", sort: "distance", area: null });
      },
      () => setLocating(false),
      { timeout: 8000 },
    );
  }

  const Chip = ({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) => (
    <button type="button" aria-pressed={active} onClick={onClick} className={clsx("chip", active && "chip-active")}>{children}</button>
  );

  return (
    <section aria-label={t("filters")} className="flex flex-col gap-4">
      <form
        role="search"
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          set({ q: String(new FormData(e.currentTarget).get("q") || "") || null, sort: null });
        }}
      >
        <label className="relative flex-1">
          <span className="sr-only">{t("what")}</span>
          <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gris" />
          <input key={q} name="q" defaultValue={q} placeholder={t("what")} className="input pl-10" />
        </label>
        <button type="submit" className="btn-primary">{t("search")}</button>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <span className="label-caps mr-1">{t("when")}</span>
        <Chip active={!sp.get("date")} onClick={() => set({ date: null })}>{t("anyDate")}</Chip>
        <Chip active={sp.get("date") === "today"} onClick={() => set({ date: "today" })}>{t("today")}</Chip>
        <Chip active={sp.get("date") === "tomorrow"} onClick={() => set({ date: "tomorrow" })}>{t("tomorrow")}</Chip>
        <Chip active={sp.get("date") === "weekend"} onClick={() => set({ date: "weekend" })}>{t("weekend")}</Chip>
        <label className="chip cursor-pointer">
          <Icon name="calendar" size={16} />
          <input type="date" aria-label={t("when")} className="bg-transparent text-sm outline-none" value={/^\d{4}-\d{2}-\d{2}$/.test(sp.get("date") ?? "") ? sp.get("date")! : ""} onChange={(e) => set({ date: e.target.value || null })} />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="label-caps mr-1">{t("where")}</span>
        <label className="chip cursor-pointer">
          <Icon name="pin" size={16} />
          <select aria-label={t("where")} className="max-w-[12rem] bg-transparent text-sm outline-none" value={sp.get("area") ?? ""} onChange={(e) => set({ area: e.target.value || null, lat: null, lon: null, radius_km: null, sort: sp.get("sort") === "distance" ? null : sp.get("sort") })}>
            <option value="">{t("anyArea")}</option>
            {areas.filter((a) => a.kind === "MUNICIPALITY").map((m) => (
              <optgroup key={m.slug} label={localized(m.name as Record<string, string>, locale)}>
                <option value={m.slug}>{localized(m.name as Record<string, string>, locale)}</option>
                {areas.filter((a) => a.parent === m.slug).map((n) => (
                  <option key={n.slug} value={n.slug}>— {localized(n.name as Record<string, string>, locale)}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <Chip active={!!sp.get("lat")} onClick={sp.get("lat") ? () => set({ lat: null, lon: null, radius_km: null, sort: null }) : nearMe}>
          <Icon name="pin" size={16} /> {locating ? "…" : t("nearMe")}
        </Chip>
        {sp.get("lat") && (
          <select aria-label="Rayon" className="chip" value={sp.get("radius_km") ?? "3"} onChange={(e) => set({ radius_km: e.target.value })}>
            {["1", "2", "3", "5", "10"].map((r) => <option key={r} value={r}>{r} km</option>)}
          </select>
        )}
      </div>

      <div className="scrollbar-none -mx-4 flex gap-2 overflow-x-auto px-4 sm:mx-0 sm:flex-wrap sm:px-0">
        <Chip active={!sp.get("category")} onClick={() => set({ category: null })}>{t("anyCategory")}</Chip>
        {categories.filter((c) => !c.parent).map((c) => {
          const total = (counts[c.slug] ?? 0) + categories.filter((child) => child.parent === c.slug).reduce((sum, child) => sum + (counts[child.slug] ?? 0), 0);
          return (
            <Chip key={c.slug} active={sp.get("category") === c.slug} onClick={() => set({ category: c.slug })}>
              {localized(c.name as Record<string, string>, locale)}
              {total > 0 && <span className="text-xs opacity-70">{total}</span>}
            </Chip>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Chip active={!!sp.get("free")} onClick={() => toggle("free")}>{t("free")}</Chip>
        <Chip active={!!sp.get("family")} onClick={() => toggle("family")}>{t("family")}</Chip>
        <Chip active={!!sp.get("accessible")} onClick={() => toggle("accessible")}><Icon name="wheelchair" size={16} /> {t("accessible")}</Chip>
        <Chip active={!!sp.get("include_online")} onClick={() => toggle("include_online")}><Icon name="globe" size={16} /> {t("online")}</Chip>
        <label className="chip ml-auto cursor-pointer">
          <span className="text-gris">{t("sort")}</span>
          <select aria-label={t("sort")} className="bg-transparent text-sm font-semibold outline-none" value={sp.get("sort") ?? (q ? "relevance" : "date")} onChange={(e) => set({ sort: e.target.value })}>
            <option value="date">{t("sortDate")}</option>
            {q && <option value="relevance">{t("sortRelevance")}</option>}
            {sp.get("lat") && <option value="distance">{t("sortDistance")}</option>}
          </select>
        </label>
        {[...sp.keys()].some((k) => k !== "cursor") && (
          <button type="button" className="btn-ghost text-sm" onClick={() => startTransition(() => router.replace("?", { scroll: false }))}>
            <Icon name="x" size={16} /> {t("reset")}
          </button>
        )}
      </div>
    </section>
  );
}
