import type { EventCard as EventCardType } from "@wigo/shared";
import clsx from "clsx";
import Image from "next/image";
import { useLocale, useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { cardGradient, formatDateTime, formatPrice, localized } from "@/lib/format";

import { Badge } from "./Badge";
import { FavoriteButton } from "./FavoriteButton";
import { Icon } from "./Icon";

/** Carte événement 4:5 (UI-03, §7.3) : dégradé, cercles concentriques, badges, cœur favori. */
export function EventCard({ event, compact = false }: { event: EventCardType; compact?: boolean }) {
  const locale = useLocale();
  const t = useTranslations("card");
  const category = localized(event.primary_category?.name as Record<string, string>, locale);
  const when = formatDateTime(event.next_start ?? event.first_start, locale);
  const price = formatPrice(event.pricing, locale, { free: t("free"), pwyw: t("pwyw"), from: t("from") });
  const cancelled = event.status === "CANCELLED";

  return (
    <article className={clsx("group relative flex flex-col", compact ? "w-56 shrink-0" : "")}>
      <Link href={{ pathname: "/evenements/[slug]", params: { slug: event.slug } }} className="block rounded-card focus-visible:ring-2">
        <div className="relative aspect-poster overflow-hidden rounded-card bg-rings shadow-card" style={{ background: event.poster?.url ? undefined : cardGradient(event.slug) }}>
          {event.poster?.url ? (
            <Image src={event.poster.url} alt={event.poster.alt_text || ""} fill sizes="(max-width: 640px) 50vw, 280px" className="object-cover transition-transform duration-500 group-hover:scale-[1.03]" />
          ) : (
            <div className="absolute inset-0 bg-rings" aria-hidden="true" />
          )}
          <div className="absolute inset-x-0 top-0 flex flex-wrap items-start gap-1.5 p-3">
            <Badge tone="sable">{category}</Badge>
            {event.visibility === "FEATURED" && <Badge tone="or"><Icon name="star" size={12} /> {t("featured")}</Badge>}
            {event.visibility === "PARTNER" && <Badge tone="nuit">{t("partner")}</Badge>}
            {event.is_long && <Badge tone="encre">{t("ongoing")}</Badge>}
            {cancelled && <Badge tone="danger">{t("cancelled")}</Badge>}
            {event.format === "ONLINE" && <Badge tone="nuit"><Icon name="globe" size={12} /> {t("online")}</Badge>}
          </div>
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-encre/85 via-encre/40 to-transparent p-3 pt-10 text-papier">
            <p className="text-xs font-semibold uppercase tracking-wide text-sable">{when}</p>
            <h3 className={clsx("mt-1 font-display font-extrabold leading-tight text-papier", compact ? "text-base" : "text-lg sm:text-xl", cancelled && "line-through")}>{event.title}</h3>
          </div>
        </div>
      </Link>
      <FavoriteButton slug={event.slug} className="absolute right-3 top-3 translate-y-9 sm:translate-y-0 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100" />
      <div className="mt-2.5 flex items-start justify-between gap-2 px-1 text-sm">
        <p className="flex min-w-0 items-center gap-1 text-gris">
          <Icon name="pin" size={14} className="shrink-0" />
          <span className="truncate">{event.venue?.name ?? t("online")}{event.venue?.city && event.venue.city !== "Bruxelles" ? ` · ${event.venue.city}` : ""}</span>
        </p>
        <p className="shrink-0 font-semibold">{price}</p>
      </div>
      <p className="flex items-center gap-1 px-1 text-xs text-gris">
        {event.organizer.verified && <Icon name="check" size={12} className="text-nuit" />}
        <span className="truncate">{event.organizer.name}</span>
        {event.distance_km != null && <span>· {t("km", { km: event.distance_km })}</span>}
        {event.age_policy === "ADULTS_ONLY" && <span className="ml-auto font-bold text-brique">{t("adults")}</span>}
      </p>
    </article>
  );
}

export function EventGrid({ events, emptyLabel }: { events: EventCardType[]; emptyLabel?: string }) {
  if (!events.length) return emptyLabel ? <p className="text-gris">{emptyLabel}</p> : null;
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-7 sm:grid-cols-3 lg:grid-cols-4">
      {events.map((e) => (
        <EventCard key={e.id} event={e} />
      ))}
    </div>
  );
}

export function EventRail({ events }: { events: EventCardType[] }) {
  return (
    <div className="scrollbar-none -mx-4 flex snap-x gap-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
      {events.map((e) => (
        <div key={e.id} className="snap-start">
          <EventCard event={e} compact />
        </div>
      ))}
    </div>
  );
}
