"use client";

import { useLocale, useTranslations } from "next-intl";
import { useParams } from "next/navigation";

import { Link, usePathname } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const locale = useLocale();
  const pathname = usePathname();
  const params = useParams();
  const t = useTranslations("nav");
  return (
    <nav aria-label={t("language")} className={`flex items-center gap-1 text-sm font-semibold ${className}`}>
      {routing.locales.map((l, i) => (
        <span key={l} className="flex items-center">
          {i > 0 && <span aria-hidden="true" className="px-1 text-gris">·</span>}
          <Link
            // @ts-expect-error les params dynamiques sont réutilisés tels quels
            href={{ pathname, params }}
            locale={l}
            hrefLang={l}
            aria-current={l === locale ? "true" : undefined}
            className={`rounded px-1 uppercase ${l === locale ? "text-encre underline decoration-brique decoration-2 underline-offset-4" : "text-gris hover:text-encre"}`}
          >
            {l}
          </Link>
        </span>
      ))}
    </nav>
  );
}
