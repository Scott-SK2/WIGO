import type { Metadata } from "next";
import { getLocale, getTranslations, setRequestLocale } from "next-intl/server";

import { Icon } from "@/components/Icon";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { localized } from "@/lib/format";

export const revalidate = 3600;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav");
  return { title: t("areas") };
}

/** SEO-01 : pages par commune et quartier (liens vers l'explorateur filtré). */
export default async function AreasPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const [areas, t, lang] = await Promise.all([api.areas(), getTranslations("nav"), getLocale()]);
  const munis = areas.filter((a) => a.kind === "MUNICIPALITY");
  return (
    <div className="container-wigo py-8">
      <h1 className="section-title">{t("areas")}</h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {munis.map((m) => (
          <div key={m.slug} className="rounded-card border border-sable bg-white p-4">
            <Link href={{ pathname: "/explorer", query: { area: m.slug } }} className="flex items-center justify-between font-display text-xl font-extrabold hover:text-brique">
              {localized(m.name as Record<string, string>, lang)} <Icon name="arrow" size={18} />
            </Link>
            <p className="mt-1 text-xs text-gris">{(m.postal_codes as string[]).join(", ")}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {areas.filter((a) => a.parent === m.slug).map((n) => (
                <Link key={n.slug} href={{ pathname: "/explorer", query: { area: n.slug } }} className="chip min-h-8 px-3 text-xs">{localized(n.name as Record<string, string>, lang)}</Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
