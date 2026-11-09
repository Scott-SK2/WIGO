"use client";

import clsx from "clsx";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { readFavorites, subscribeFavorites, toggleFavorite } from "@/lib/favorites";

import { Icon } from "./Icon";

export function FavoriteButton({ slug, className, size = 20 }: { slug: string; className?: string; size?: number }) {
  const t = useTranslations("card");
  const [active, setActive] = useState(false);
  useEffect(() => {
    const sync = () => setActive(readFavorites().includes(slug));
    sync();
    return subscribeFavorites(sync);
  }, [slug]);
  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={active ? t("unfavorite") : t("favorite")}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setActive(toggleFavorite(slug));
      }}
      className={clsx(
        "inline-flex h-11 w-11 items-center justify-center rounded-full border transition-colors",
        active ? "border-brique bg-brique text-papier" : "border-white/60 bg-white/80 text-encre hover:bg-white",
        className,
      )}
    >
      <Icon name="heart" size={size} fill={active ? "currentColor" : "none"} />
    </button>
  );
}
