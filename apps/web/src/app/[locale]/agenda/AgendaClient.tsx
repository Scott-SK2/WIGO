"use client";

import type { EventCard as EventCardType } from "@wigo/shared";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { EventGrid } from "@/components/EventCard";
import { Link } from "@/i18n/navigation";
import { readFavorites, subscribeFavorites, writeFavorites } from "@/lib/favorites";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AgendaClient() {
  const t = useTranslations("agenda");
  const tc = useTranslations("common");
  const [slugs, setSlugs] = useState<string[] | null>(null);
  const [events, setEvents] = useState<EventCardType[]>([]);

  useEffect(() => {
    const sync = () => setSlugs(readFavorites());
    sync();
    return subscribeFavorites(sync);
  }, []);

  useEffect(() => {
    if (!slugs || !slugs.length) {
      setEvents([]);
      return;
    }
    let cancelled = false;
    Promise.all(
      slugs.map((s) =>
        fetch(`${API}/api/v1/events/${encodeURIComponent(s)}`)
          .then((r) => (r.ok ? (r.json() as Promise<EventCardType>) : null))
          .catch(() => null),
      ),
    ).then((rows) => {
      if (cancelled) return;
      const found = rows.filter((r): r is EventCardType => r != null);
      // Nettoyage des favoris dont la fiche n'existe plus
      const gone = slugs.filter((s) => !found.some((e) => e.slug === s));
      if (gone.length && rows.every((r) => r !== undefined)) writeFavorites(slugs.filter((s) => !gone.includes(s)));
      setEvents(found.sort((a, b) => (a.next_start ?? "").localeCompare(b.next_start ?? "")));
    });
    return () => {
      cancelled = true;
    };
  }, [slugs]);

  if (slugs === null) return <p className="mt-8 text-gris">{tc("loading")}</p>;
  if (!slugs.length)
    return (
      <div className="mt-8">
        <EmptyState title={t("empty")} text={t("emptyText")}>
          <Link href="/explorer" className="btn-primary">{t("explore")}</Link>
        </EmptyState>
      </div>
    );
  return (
    <div className="mt-8">
      <EventGrid events={events} />
      <p className="mt-8 text-sm text-gris">
        <Link href="/compte/connexion" className="underline underline-offset-4">{t("sync")}</Link>
      </p>
    </div>
  );
}
