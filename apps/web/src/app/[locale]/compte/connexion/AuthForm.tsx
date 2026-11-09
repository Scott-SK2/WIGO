"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Link } from "@/i18n/navigation";
import { readFavorites } from "@/lib/favorites";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKENS = "wigo:auth:v1";

type Mode = "login" | "register" | "forgot";

export function AuthForm() {
  const t = useTranslations("account");
  const locale = useLocale();
  const [mode, setMode] = useState<Mode>("login");
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [me, setMe] = useState<{ email: string; email_verified: boolean } | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem(TOKENS);
    if (!raw) return;
    const { access } = JSON.parse(raw) as { access: string };
    fetch(`${API}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${access}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((u) => u && setMe(u))
      .catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    const form = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>;
    try {
      if (mode === "login") {
        const r = await fetch(`${API}/api/v1/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: form.email, password: form.password }) });
        if (!r.ok) throw new Error((await r.json())?.error?.message ?? t("error"));
        const tokens = await r.json();
        window.localStorage.setItem(TOKENS, JSON.stringify(tokens));
        // UI-05 : fusion des favoris locaux
        const favs = readFavorites();
        if (favs.length) await fetch(`${API}/api/v1/me/favorites`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${tokens.access}` }, body: JSON.stringify({ events: favs }) });
        const u = await fetch(`${API}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${tokens.access}` } }).then((x) => x.json());
        setMe(u);
        setMessage({ kind: "ok", text: t("loggedIn") });
      } else if (mode === "register") {
        const r = await fetch(`${API}/api/v1/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: form.email, password: form.password, display_name: form.display_name, language: locale, accept_terms: form.accept_terms === "on" }) });
        if (!r.ok) {
          const body = await r.json();
          const details = body?.error?.details;
          throw new Error(details ? Object.values(details).flat().join(" ") : body?.error?.message ?? t("error"));
        }
        setMessage({ kind: "ok", text: t("registered") });
      } else {
        await fetch(`${API}/api/v1/auth/password-reset`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: form.email }) });
        setMessage({ kind: "ok", text: t("resetRequested") });
      }
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : t("error") });
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    const raw = window.localStorage.getItem(TOKENS);
    if (raw) {
      const { refresh, access } = JSON.parse(raw);
      await fetch(`${API}/api/v1/auth/logout`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}` }, body: JSON.stringify({ refresh }) }).catch(() => undefined);
    }
    window.localStorage.removeItem(TOKENS);
    setMe(null);
    setMessage(null);
  }

  if (me) {
    return (
      <div className="panel">
        <p className="label-caps text-brique">WIGO</p>
        <h1 className="mt-2 text-3xl">{t("loggedIn")}</h1>
        <p className="mt-2 text-gris">{me.email}{me.email_verified ? "" : ` · ${t("registered")}`}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Link href="/publier" className="btn-primary">+ Publier</Link>
          <button type="button" onClick={logout} className="btn-outline">{t("logout")}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="flex gap-2" role="tablist">
        <button role="tab" aria-selected={mode === "login"} className={`chip ${mode === "login" ? "chip-active" : ""}`} onClick={() => setMode("login")}>{t("login")}</button>
        <button role="tab" aria-selected={mode === "register"} className={`chip ${mode === "register" ? "chip-active" : ""}`} onClick={() => setMode("register")}>{t("register")}</button>
      </div>
      <h1 className="mt-5 text-3xl">{mode === "forgot" ? t("forgot") : mode === "login" ? t("login") : t("register")}</h1>
      <form onSubmit={submit} className="mt-5 flex flex-col gap-3" aria-busy={busy}>
        <label className="flex flex-col gap-1 text-sm font-semibold">
          {t("email")}
          <input name="email" type="email" required autoComplete="email" className="input" />
        </label>
        {mode !== "forgot" && (
          <label className="flex flex-col gap-1 text-sm font-semibold">
            {t("password")}
            <input name="password" type="password" required minLength={10} autoComplete={mode === "login" ? "current-password" : "new-password"} className="input" />
            {mode === "register" && <span className="text-xs font-normal text-gris">{t("passwordHint")}</span>}
          </label>
        )}
        {mode === "register" && (
          <>
            <label className="flex flex-col gap-1 text-sm font-semibold">
              {t("displayName")}
              <input name="display_name" className="input" maxLength={80} />
            </label>
            <label className="flex items-start gap-2 text-sm text-gris">
              <input name="accept_terms" type="checkbox" required className="mt-1 h-4 w-4 accent-brique" />
              <span>{t("acceptTerms")}</span>
            </label>
          </>
        )}
        <button type="submit" className="btn-primary mt-2" disabled={busy}>
          {mode === "login" ? t("submitLogin") : mode === "register" ? t("submitRegister") : t("resetRequest")}
        </button>
        {message && <p role={message.kind === "error" ? "alert" : "status"} className={message.kind === "error" ? "text-sm text-[#B3261E]" : "text-sm font-semibold text-nuit"}>{message.text}</p>}
      </form>
      <p className="mt-4 text-sm text-gris">
        {mode === "login" ? (
          <>
            <button type="button" className="underline underline-offset-4" onClick={() => setMode("forgot")}>{t("forgot")}</button>
            {" · "}
            {t("noAccount")} <button type="button" className="underline underline-offset-4" onClick={() => setMode("register")}>{t("register")}</button>
          </>
        ) : (
          <>
            {t("hasAccount")} <button type="button" className="underline underline-offset-4" onClick={() => setMode("login")}>{t("login")}</button>
          </>
        )}
      </p>
    </div>
  );
}
