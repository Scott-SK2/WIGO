"use client";

import type { Area } from "@wigo/shared";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { localized } from "@/lib/format";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function NewsletterForm({ areas = [], compact = false }: { areas?: Area[]; compact?: boolean }) {
  const t = useTranslations("newsletter");
  const locale = useLocale();
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setState("sending");
    try {
      const res = await fetch(`${API}/api/v1/newsletter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), area: form.get("area") || null, language: locale, consent: form.get("consent") === "on" }),
      });
      setState(res.ok ? "sent" : "error");
    } catch {
      setState("error");
    }
  }

  if (state === "sent") return <p role="status" className="rounded-xl bg-white/70 p-4 font-semibold text-nuit">{t("sent")}</p>;

  return (
    <form onSubmit={submit} className="flex flex-col gap-3" aria-busy={state === "sending"}>
      <div className={compact ? "flex flex-col gap-2 sm:flex-row" : "grid gap-3 sm:grid-cols-2"}>
        <label className="flex-1">
          <span className="sr-only">{t("email")}</span>
          <input name="email" type="email" required autoComplete="email" placeholder={t("email")} className="input" />
        </label>
        {areas.length > 0 && (
          <label className="flex-1">
            <span className="sr-only">{t("area")}</span>
            <select name="area" className="input" defaultValue="">
              <option value="">{t("area")}</option>
              {areas.filter((a) => a.kind === "MUNICIPALITY").map((a) => (
                <option key={a.slug} value={a.slug}>{localized(a.name as Record<string, string>, locale)}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      <label className="flex items-start gap-2 text-sm text-gris">
        <input name="consent" type="checkbox" required className="mt-1 h-4 w-4 accent-brique" />
        <span>{t("consent")}</span>
      </label>
      <div className="flex items-center gap-3">
        <button type="submit" className="btn-brique" disabled={state === "sending"}>{t("submit")}</button>
        {state === "error" && <p role="alert" className="text-sm text-[#B3261E]">{t("error")}</p>}
      </div>
    </form>
  );
}
