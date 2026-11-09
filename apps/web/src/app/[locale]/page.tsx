import type { Metadata } from "next";
import { getLocale, getTranslations, setRequestLocale } from "next-intl/server";

import { EventGrid, EventRail } from "@/components/EventCard";
import { Icon } from "@/components/Icon";
import { NewsletterForm } from "@/components/NewsletterForm";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { localized } from "@/lib/format";

export const revalidate = 120;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("home");
  return { title: { absolute: `WIGO — ${t("title")}` }, description: t("subtitle") };
}

/** SCR-01 : Accueil — recherche, Ce soir / Demain / Ce week-end, catégories, sélection, newsletter. */
export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const [t, home, categories, areas] = await Promise.all([getTranslations("home"), api.home(), api.categories(), api.areas()]);
  const lang = await getLocale();
  const shortcuts: Array<{ label: string; query: Record<string, string> }> = [
    { label: t("tonight"), query: { date: "today" } },
    { label: t("tomorrow"), query: { date: "tomorrow" } },
    { label: t("weekend"), query: { date: "weekend" } },
    { label: t("free"), query: { free: "1" } },
    { label: t("family"), query: { family: "1" } },
    { label: t("accessible"), query: { accessible: "1" } },
  ];

  return (
    <>
      <section className="bg-creme">
        <div className="container-wigo grid items-center gap-8 py-12 sm:py-16 lg:grid-cols-[1.3fr_1fr]">
          <div>
            <p className="label-caps text-brique">Bruxelles · Brussel · Brussels</p>
            <h1 className="mt-3 text-4xl leading-[1.05] sm:text-5xl lg:text-6xl">{t("title")}</h1>
            <p className="mt-4 max-w-xl text-lg text-gris">{t("subtitle")}</p>
            <form action={`/${lang}/${lang === "nl" ? "verkennen" : lang === "en" ? "explore" : "explorer"}`} method="get" role="search" className="mt-6 flex max-w-xl gap-2">
              <label className="relative flex-1">
                <span className="sr-only">{t("search")}</span>
                <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gris" />
                <input name="q" placeholder={t("searchPlaceholder")} className="input pl-10" />
              </label>
              <button type="submit" className="btn-primary">{t("search")}</button>
            </form>
            <div className="mt-4 flex flex-wrap gap-2">
              {shortcuts.map((s) => (
                <Link key={s.label} href={{ pathname: "/explorer", query: s.query }} className="chip">{s.label}</Link>
              ))}
            </div>
            <p className="mt-4 text-sm text-gris">{t("activeEvents", { count: home.counts.active_events })}</p>
          </div>
          <div className="hidden lg:block">
            <div className="relative mx-auto aspect-poster w-72 rotate-[-4deg] rounded-panel bg-brique bg-rings shadow-panel">
              <div className="absolute inset-x-0 bottom-0 p-6 text-papier">
                <p className="label-caps text-sable">{t("selection")}</p>
                <p className="mt-2 font-display text-3xl font-black leading-tight">WIGO</p>
                <p className="text-sable">{t("weekendTitle")}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container-wigo mt-10">
        <h2 className="label-caps">{t("categories")}</h2>
        <div className="scrollbar-none -mx-4 mt-3 flex gap-2 overflow-x-auto px-4 sm:mx-0 sm:flex-wrap sm:px-0">
          {categories.filter((c) => !c.parent).map((c) => (
            <Link key={c.slug} href={{ pathname: "/explorer", query: { category: c.slug } }} className="chip">
              {localized(c.name as Record<string, string>, lang)}
            </Link>
          ))}
        </div>
      </section>

      {home.selection.length > 0 && (
        <section className="container-wigo mt-12">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="section-title flex items-center gap-2"><Icon name="star" className="text-or" /> {t("selection")}</h2>
              <p className="mt-1 text-gris">{t("selectionIntro")}</p>
            </div>
            <Link href={{ pathname: "/explorer", query: { date: "weekend" } }} className="btn-ghost hidden sm:inline-flex">{t("seeAll")} <Icon name="arrow" size={16} /></Link>
          </div>
          <div className="mt-5"><EventRail events={home.selection} /></div>
        </section>
      )}

      <Section title={t("tonightTitle")} events={home.tonight} more={{ date: "today" }} moreLabel={t("seeAll")} />
      <Section title={t("weekendTitle")} events={home.weekend} more={{ date: "weekend" }} moreLabel={t("seeAll")} />
      <Section title={t("freeTitle")} events={home.free} more={{ free: "1" }} moreLabel={t("seeAll")} />
      {home.ongoing.length > 0 && <Section title={t("ongoingTitle")} events={home.ongoing} more={{ date: "today" }} moreLabel={t("seeAll")} />}

      <section className="container-wigo mt-16 grid gap-6 lg:grid-cols-2">
        <div className="panel bg-brique text-papier">
          <p className="label-caps text-sable">{t("publishCta")}</p>
          <h2 className="mt-2 font-display text-3xl font-black">{t("publishButton")}</h2>
          <p className="mt-3 text-sable">{t("publishText")}</p>
          <Link href="/publier" className="btn mt-6 bg-papier text-encre hover:bg-creme">{t("publishButton")} <Icon name="arrow" size={16} /></Link>
        </div>
        <div className="panel">
          <p className="label-caps text-brique">Newsletter</p>
          <h2 className="mt-2 font-display text-3xl font-black">{t("newsletterTitle")}</h2>
          <p className="mt-3 text-gris">{t("newsletterText")}</p>
          <div className="mt-5"><NewsletterForm areas={areas} compact /></div>
        </div>
      </section>
    </>
  );
}

function Section({ title, events, more, moreLabel }: { title: string; events: Parameters<typeof EventGrid>[0]["events"]; more: Record<string, string>; moreLabel: string }) {
  if (!events.length) return null;
  return (
    <section className="container-wigo mt-12">
      <div className="flex items-end justify-between gap-4">
        <h2 className="section-title">{title}</h2>
        <Link href={{ pathname: "/explorer", query: more }} className="btn-ghost">{moreLabel} <Icon name="arrow" size={16} /></Link>
      </div>
      <div className="mt-5"><EventGrid events={events.slice(0, 8)} /></div>
    </section>
  );
}
