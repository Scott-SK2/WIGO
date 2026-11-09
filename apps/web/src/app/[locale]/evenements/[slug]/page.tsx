import type { Metadata } from "next";
import { getLocale, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import Image from "next/image";

import { Badge } from "@/components/Badge";
import { FavoriteButton } from "@/components/FavoriteButton";
import { Icon } from "@/components/Icon";
import { ShareButton } from "@/components/ShareButton";
import { Link } from "@/i18n/navigation";
import { api, ApiError, PUBLIC_API_URL } from "@/lib/api";
import { cardGradient, formatDay, formatPrice, formatTime, localized } from "@/lib/format";

export const revalidate = 60;
const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

async function load(slug: string) {
  try {
    return await api.event(slug);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 403)) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string; slug: string }> }): Promise<Metadata> {
  const { slug, locale } = await params;
  const event = await load(slug);
  const description = (event.description ?? "").slice(0, 160);
  return {
    title: event.title,
    description,
    alternates: { canonical: event.urls.canonical, languages: { fr: event.urls.fr, nl: event.urls.nl, en: event.urls.en } },
    openGraph: { title: event.title, description, type: "article", locale, images: event.poster?.url ? [event.poster.url] : undefined },
    robots: event.status === "PUBLISHED" ? undefined : { index: false },
  };
}

/** SCR-04 : fiche événement — affiche, séances, lieu, prix, accessibilité, billetterie, calendrier, partage, schema.org. */
export default async function EventPage({ params }: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [event, t, tc] = await Promise.all([load(slug), getTranslations("event"), getTranslations("card")]);
  const lang = await getLocale();
  const price = formatPrice(event.pricing, lang, { free: tc("free"), pwyw: tc("pwyw"), from: tc("from") });
  const upcoming = event.occurrences.filter((o) => new Date(o.ends_at) >= new Date() || event.status !== "PUBLISHED");
  const icsUrl = `${PUBLIC_API_URL}/api/v1/events/${event.slug}/ics`;
  const first = upcoming[0];
  const gcal = first
    ? `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(event.title)}&dates=${iso(first.starts_at)}/${iso(first.ends_at)}&details=${encodeURIComponent(event.urls.canonical)}&location=${encodeURIComponent(event.venue ? `${event.venue.name}, ${event.venue.address}` : "")}`
    : null;
  const directions = event.venue?.location ? `https://www.openstreetmap.org/directions?to=${event.venue.location.lat}%2C${event.venue.location.lon}` : null;
  const access: Record<string, boolean | string | null | undefined> = { ...(event.accessibility ?? {}) };
  const accessRows = [
    ["wheelchair", t("wheelchair")],
    ["adapted_toilets", t("adaptedToilets")],
    ["hearing_loop", t("hearingLoop")],
    ["sign_language", t("signLanguage")],
    ["sensory_friendly", t("sensoryFriendly")],
  ] as const;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Event",
    name: event.title,
    description: event.description,
    url: event.urls.canonical,
    image: event.poster?.url,
    startDate: first?.starts_at,
    endDate: upcoming.at(-1)?.ends_at,
    eventStatus: event.status === "CANCELLED" ? "https://schema.org/EventCancelled" : "https://schema.org/EventScheduled",
    eventAttendanceMode: event.format === "ONLINE" ? "https://schema.org/OnlineEventAttendanceMode" : event.format === "HYBRID" ? "https://schema.org/MixedEventAttendanceMode" : "https://schema.org/OfflineEventAttendanceMode",
    location: event.venue
      ? { "@type": "Place", name: event.venue.name, address: { "@type": "PostalAddress", streetAddress: `${event.venue.street} ${event.venue.house_number}`.trim(), postalCode: event.venue.postal_code, addressLocality: event.venue.city, addressCountry: event.venue.country }, geo: event.venue.location ? { "@type": "GeoCoordinates", latitude: event.venue.location.lat, longitude: event.venue.location.lon } : undefined }
      : { "@type": "VirtualLocation", url: event.online_url },
    organizer: { "@type": "Organization", name: event.organizer.name, url: event.organizer.slug ? `${SITE}/${lang}/organisateurs/${event.organizer.slug}` : undefined },
    offers: { "@type": "Offer", price: event.pricing.type === "FREE" ? 0 : event.pricing.min ?? undefined, priceCurrency: event.pricing.currency, url: event.ticketing?.url ?? event.urls.canonical, availability: "https://schema.org/InStock" },
    inLanguage: event.languages ?? [],
  };

  return (
    <article className="container-wigo py-8">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      {event.status === "CANCELLED" && <p role="alert" className="mb-6 rounded-xl bg-[#B3261E] px-4 py-3 font-semibold text-papier">{t("cancelledBanner")}</p>}
      {event.status === "ARCHIVED" && <p role="status" className="mb-6 rounded-xl bg-sable px-4 py-3 font-semibold">{t("archivedBanner")}</p>}

      <div className="grid gap-8 lg:grid-cols-[2fr_3fr]">
        <div className="relative aspect-poster overflow-hidden rounded-panel bg-rings shadow-panel" style={{ background: event.poster?.url ? undefined : cardGradient(event.slug) }}>
          {event.poster?.url ? <Image src={event.poster.url} alt={event.poster.alt_text || event.title} fill priority sizes="(max-width: 1024px) 100vw, 40vw" className="object-cover" /> : <div className="absolute inset-0 bg-rings" aria-hidden="true" />}
          <div className="absolute left-4 top-4 flex flex-wrap gap-1.5">
            <Badge tone="sable">{localized(event.primary_category?.name as Record<string, string>, lang)}</Badge>
            {event.secondary_categories.map((c) => <Badge key={c.slug} tone="sable">{localized(c.name as Record<string, string>, lang)}</Badge>)}
            {event.visibility === "FEATURED" && <Badge tone="or"><Icon name="star" size={12} /> {tc("featured")}</Badge>}
            {event.visibility === "PARTNER" && <Badge tone="nuit">{tc("partner")}</Badge>}
          </div>
          <FavoriteButton slug={event.slug} className="absolute right-4 top-4" />
        </div>

        <div>
          <p className="label-caps text-brique">{first ? formatDay(first.starts_at, lang) : ""}</p>
          <h1 className="mt-2 text-3xl leading-tight sm:text-4xl lg:text-5xl">{event.title}</h1>
          <p className="mt-3 flex items-center gap-2 text-gris">
            {t("by")}{" "}
            {event.organizer.slug ? (
              <Link href={{ pathname: "/organisateurs/[slug]", params: { slug: event.organizer.slug } }} className="font-semibold text-encre underline-offset-4 hover:underline">{event.organizer.name}</Link>
            ) : (
              <span className="font-semibold text-encre">{event.organizer.name}</span>
            )}
            {event.organizer.verified && <Badge tone="nuit"><Icon name="check" size={12} /> {tc("verified")}</Badge>}
          </p>

          <div className="mt-6 flex flex-wrap gap-2">
            {event.ticketing && (
              <a href={`${PUBLIC_API_URL}/api/v1/events/${event.slug}/out`} target="_blank" rel="noopener noreferrer nofollow" className="btn-brique">
                <Icon name="ticket" size={18} /> {t("tickets")}
              </a>
            )}
            {event.online_url && event.format !== "ONSITE" && (
              <a href={event.online_url} target="_blank" rel="noopener noreferrer" className="btn-primary"><Icon name="globe" size={18} /> {t("join")}</a>
            )}
            <a href={icsUrl} className="btn-outline" download><Icon name="calendar" size={18} /> {t("addToCalendar")}</a>
            <ShareButton title={event.title} url={event.urls.canonical} />
          </div>
          {event.ticketing && <p className="mt-2 text-xs text-gris">{t("ticketsNote")}</p>}

          <dl className="mt-8 grid gap-6 sm:grid-cols-2">
            <div>
              <dt className="label-caps">{t("dates")}</dt>
              <dd className="mt-2 space-y-1.5">
                {upcoming.map((o) => (
                  <div key={o.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-creme px-3 py-2">
                    <span className="font-semibold capitalize">{formatDay(o.starts_at, lang)}</span>
                    <span className="text-gris">{formatTime(o.starts_at, lang)} – {formatTime(o.ends_at, lang)}</span>
                    {o.status === "SOLD_OUT" && <Badge tone="encre">{tc("soldOut")}</Badge>}
                    {o.status === "CANCELLED" && <Badge tone="danger">{tc("cancelled")}</Badge>}
                    {o.status === "POSTPONED" && <Badge tone="brique">{tc("postponed")}</Badge>}
                  </div>
                ))}
              </dd>
              <p className="mt-2 flex flex-wrap gap-3 text-sm">
                <a href={icsUrl} className="underline underline-offset-4">{t("ics")}</a>
                {gcal && <a href={gcal} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">{t("google")}</a>}
              </p>
            </div>
            <div>
              <dt className="label-caps">{t("venue")}</dt>
              <dd className="mt-2">
                {event.venue ? (
                  <>
                    <p className="font-semibold">{event.venue.name}</p>
                    <p className="text-gris">{event.venue.address}</p>
                    {directions && <a href={directions} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm underline underline-offset-4"><Icon name="pin" size={14} /> {t("directions")}</a>}
                  </>
                ) : (
                  <p className="flex items-center gap-1"><Icon name="globe" size={16} /> {tc("online")}</p>
                )}
              </dd>
              <dt className="label-caps mt-5">{t("price")}</dt>
              <dd className="mt-1 font-semibold">
                {price}
                {event.pricing.details && <span className="block text-sm font-normal text-gris">{event.pricing.details}</span>}
                {event.registration_required && <span className="block text-sm font-normal text-gris">{t("registration")}</span>}
              </dd>
              <dt className="label-caps mt-5">{t("access")}</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                <Badge tone={event.age_policy === "ADULTS_ONLY" ? "brique" : "sable"}>
                  {event.age_policy === "ALL" ? t("allAges") : event.age_policy === "ADULTS_ONLY" ? tc("adults") : tc("minAge", { age: event.min_age ?? "" })}
                </Badge>
                {event.is_family_friendly && <Badge tone="sable">{tc("family")}</Badge>}
                {(event.languages ?? []).map((l) => <Badge key={l} tone="sable">{l.toUpperCase()}</Badge>)}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="mt-12 grid gap-10 lg:grid-cols-[3fr_2fr]">
        <section>
          <h2 className="label-caps">Description</h2>
          <div className="prose-wigo mt-3 whitespace-pre-line text-[17px] leading-relaxed">{event.description}</div>
          {event.tags.length > 0 && (
            <p className="mt-6 flex flex-wrap gap-2">{event.tags.map((tag) => <span key={tag.slug} className="chip">#{localized(tag.name as Record<string, string>, lang)}</span>)}</p>
          )}
        </section>
        <aside>
          <h2 className="label-caps flex items-center gap-2"><Icon name="wheelchair" size={16} /> {t("accessibility")}</h2>
          <ul className="mt-3 divide-y divide-sable rounded-xl border border-sable bg-white">
            {accessRows.map(([key, label]) => (
              <li key={key} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <span>{label}</span>
                <span className={access[key] === true ? "font-semibold text-nuit" : "text-gris"}>{access[key] === true ? t("yes") : access[key] === false ? t("no") : t("unknown")}</span>
              </li>
            ))}
          </ul>
          {(access.notes || access.event_notes) && <p className="mt-2 text-sm text-gris">{[access.notes, access.event_notes].filter(Boolean).join(" ")}</p>}
          <Link href={{ pathname: "/legal/[page]", params: { page: "signalement" }, query: { event: event.slug } }} className="mt-6 inline-flex items-center gap-1 text-sm text-gris underline-offset-4 hover:underline">
            <Icon name="flag" size={14} /> {t("report")}
          </Link>
        </aside>
      </div>
    </article>
  );
}

function iso(s: string) {
  return new Date(s).toISOString().replace(/[-:]|\.\d{3}/g, "");
}
