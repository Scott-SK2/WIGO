"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CATEGORIES = ["SPAM", "ILLEGAL", "HATE", "WRONG_INFO", "DUPLICATE", "RIGHTS", "SUSPICIOUS_LINK", "OTHER"];

/** ADM-04 / RG-16 : signalement d'une fiche (anonyme possible). */
export function ReportForm({ event }: { event?: string }) {
  const t = useTranslations("legal");
  const tc = useTranslations("common");
  const [state, setState] = useState<"idle" | "sent" | "error">("idle");
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = Object.fromEntries(new FormData(e.currentTarget));
    const r = await fetch(`${API}/api/v1/reports`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) }).catch(() => null);
    setState(r?.ok ? "sent" : "error");
  }
  if (state === "sent") return <p role="status" className="panel font-semibold text-nuit">✓ {t("report")}</p>;
  return (
    <form onSubmit={submit} className="panel flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm font-semibold">
        Événement (slug)
        <input name="event" defaultValue={event} required className="input" />
      </label>
      <label className="flex flex-col gap-1 text-sm font-semibold">
        Motif
        <select name="category" className="input" defaultValue="WRONG_INFO">
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm font-semibold">
        Description
        <textarea name="description" rows={4} className="input py-2" />
      </label>
      <label className="flex flex-col gap-1 text-sm font-semibold">
        E-mail (facultatif)
        <input name="reporter_email" type="email" className="input" />
      </label>
      <button type="submit" className="btn-primary">{t("report")}</button>
      {state === "error" && <p role="alert" className="text-sm text-[#B3261E]">{tc("error")}</p>}
    </form>
  );
}
