import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { Badge } from "@/components/Badge";
import { EventGrid } from "@/components/EventCard";
import { Icon } from "@/components/Icon";
import { Link } from "@/i18n/navigation";
import { api, ApiError } from "@/lib/api";

export const revalidate = 300;

async function load(slug: string) {
  try {
    return await api.organization(slug);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const org = await load((await params).slug);
  return { title: org.name, description: org.description?.slice(0, 160) };
}

/** SCR-07 : profil public organisateur — infos, badge vérifié, événements à venir, « Revendiquer cette page ». */
export default async function OrganizerPage({ params }: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [org, t, tc] = await Promise.all([load(slug), getTranslations("organizer"), getTranslations("card")]);
  const events = await api.events({ q: org.name, page_size: "12" });
  const own = events.results.filter((e) => e.organizer.slug === org.slug);

  return (
    <div className="container-wigo py-8">
      <div className="panel flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-brique bg-rings font-display text-3xl font-black text-papier">{org.name.slice(0, 1)}</div>
        <div className="min-w-0 flex-1">
          <h1 className="text-3xl sm:text-4xl">{org.name}</h1>
          <p className="mt-2 flex flex-wrap items-center gap-2">
            {org.verified && <Badge tone="nuit"><Icon name="check" size={12} /> {tc("verified")}</Badge>}
            {org.website && <a href={org.website} target="_blank" rel="noopener noreferrer" className="text-sm underline underline-offset-4">{t("website")}</a>}
          </p>
          {org.description && <p className="mt-3 max-w-2xl text-gris">{org.description}</p>}
        </div>
        {org.is_claimable && (
          <div className="rounded-xl border border-sable bg-white p-4 text-sm sm:max-w-xs">
            <p className="font-semibold">{t("claim")}</p>
            <p className="mt-1 text-gris">{t("claimText")}</p>
            <Link href={{ pathname: "/compte/connexion", query: { claim: org.slug } }} className="btn-outline mt-3">{t("claim")}</Link>
          </div>
        )}
      </div>
      <h2 className="section-title mt-10">{t("upcoming")}</h2>
      <div className="mt-5"><EventGrid events={own} emptyLabel={t("none")} /></div>
    </div>
  );
}
