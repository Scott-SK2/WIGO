"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Link } from "@/i18n/navigation";

import { Icon } from "./Icon";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { Logo } from "./Logo";

/** Barre supérieure web (§4.3) : logo, Agenda, Quartiers, FR · NL · EN, Organisateurs, Newsletter, Publier. */
export function Header() {
  const t = useTranslations("nav");
  const [open, setOpen] = useState(false);
  const links = (
    <>
      <Link href="/explorer" className="btn-ghost">{t("explore")}</Link>
      <Link href="/agenda" className="btn-ghost">{t("agenda")}</Link>
      <Link href="/quartiers" className="btn-ghost">{t("areas")}</Link>
      <Link href="/organisateurs" className="btn-ghost">{t("organizers")}</Link>
      <Link href="/newsletter" className="btn-ghost">{t("newsletter")}</Link>
    </>
  );
  return (
    <header className="sticky top-0 z-40 border-b border-sable/70 bg-papier/90 backdrop-blur">
      <a href="#contenu" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:rounded focus:bg-encre focus:px-3 focus:py-2 focus:text-papier">
        {useTranslations("common")("skip")}
      </a>
      <div className="container-wigo flex min-h-16 items-center gap-3">
        <Link href="/" className="flex items-center gap-2.5" aria-label="WIGO">
          <Logo size={40} />
          <span className="hidden font-display text-xl font-black tracking-tight sm:inline">WIGO</span>
        </Link>
        <nav className="ml-4 hidden items-center gap-1 lg:flex" aria-label="Principal">{links}</nav>
        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitcher className="hidden md:flex" />
          <Link href="/publier" className="btn-primary hidden sm:inline-flex">{t("publish")}</Link>
          <button type="button" className="btn-ghost lg:hidden" aria-expanded={open} aria-controls="menu-mobile" onClick={() => setOpen((o) => !o)}>
            <Icon name={open ? "x" : "menu"} />
            <span className="sr-only">{t("menu")}</span>
          </button>
        </div>
      </div>
      {open && (
        <div id="menu-mobile" className="border-t border-sable/70 bg-papier lg:hidden">
          <nav className="container-wigo flex flex-col gap-1 py-3" aria-label="Mobile" onClick={() => setOpen(false)}>
            {links}
            <Link href="/publier" className="btn-primary mt-2 sm:hidden">{t("publish")}</Link>
            <LanguageSwitcher className="mt-3 justify-center md:hidden" />
          </nav>
        </div>
      )}
    </header>
  );
}
