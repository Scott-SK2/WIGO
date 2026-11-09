"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Link } from "@/i18n/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ResetForm({ token }: { token: string }) {
  const t = useTranslations("account");
  const [state, setState] = useState<"idle" | "done" | "error">("idle");
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const password = new FormData(e.currentTarget).get("password");
    const r = await fetch(`${API}/api/v1/auth/password-reset/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token, password }) }).catch(() => null);
    setState(r?.ok ? "done" : "error");
  }
  if (state === "done")
    return (
      <p role="status" className="panel">
        {t("resetDone")} <Link href="/compte/connexion" className="ml-2 underline underline-offset-4">{t("login")}</Link>
      </p>
    );
  return (
    <form onSubmit={submit} className="panel flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm font-semibold">
        {t("password")}
        <input name="password" type="password" minLength={10} required autoComplete="new-password" className="input" />
        <span className="text-xs font-normal text-gris">{t("passwordHint")}</span>
      </label>
      <button type="submit" className="btn-primary">{t("resetSubmit")}</button>
      {state === "error" && <p role="alert" className="text-sm text-[#B3261E]">{t("verifyError")}</p>}
    </form>
  );
}
