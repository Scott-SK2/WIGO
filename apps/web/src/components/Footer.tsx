import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

import { Logo } from "./Logo";

export function Footer() {
  const t = useTranslations("footer");
  const b = useTranslations("brand");
  return (
    <footer className="mt-16 bg-encre text-papier">
      <div className="container-wigo grid gap-8 py-12 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <div className="flex items-center gap-3">
            <Logo size={44} />
            <div>
              <p className="font-display text-xl font-black">WIGO</p>
              <p className="text-sm text-sable">{b("tagline")}</p>
            </div>
          </div>
          <p className="mt-4 max-w-sm text-sm text-sable/80">{t("rights")}</p>
        </div>
        <nav className="flex flex-col gap-2 text-sm" aria-label={t("legal")}>
          <p className="label-caps text-sable/70">{t("legal")}</p>
          <Link href={{ pathname: "/legal/[page]", params: { page: "confidentialite" } }} className="hover:underline">{t("privacy")}</Link>
          <Link href={{ pathname: "/legal/[page]", params: { page: "cgu" } }} className="hover:underline">{t("terms")}</Link>
          <Link href={{ pathname: "/legal/[page]", params: { page: "moderation" } }} className="hover:underline">{t("moderation")}</Link>
          <Link href={{ pathname: "/legal/[page]", params: { page: "contact" } }} className="hover:underline">{t("contact")}</Link>
        </nav>
        <nav className="flex flex-col gap-2 text-sm" aria-label="WIGO">
          <p className="label-caps text-sable/70">WIGO</p>
          <Link href="/a-propos" className="hover:underline">{t("about")}</Link>
          <Link href="/publier" className="hover:underline">+ Publier</Link>
          <Link href="/newsletter" className="hover:underline">Newsletter</Link>
          <a href="/manifest.webmanifest" className="hover:underline">{t("install")}</a>
        </nav>
      </div>
      <div className="border-t border-papier/10">
        <div className="container-wigo flex flex-wrap items-center justify-between gap-2 py-4 text-xs text-sable/70">
          <span>© {new Date().getFullYear()} WIGO · {b("by")}</span>
          <span>Bruxelles · Brussel · Brussels</span>
        </div>
      </div>
    </footer>
  );
}
