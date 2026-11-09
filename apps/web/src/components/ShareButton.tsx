"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Icon } from "./Icon";

export function ShareButton({ title, url }: { title: string; url: string }) {
  const t = useTranslations("event");
  const [copied, setCopied] = useState(false);
  async function share() {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch {
        /* annulé */
      }
    }
    await navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <button type="button" onClick={share} className="btn-outline">
      <Icon name="share" size={18} /> {copied ? t("copied") : t("share")}
    </button>
  );
}
