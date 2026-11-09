import clsx from "clsx";
import type { ReactNode } from "react";

type Tone = "or" | "nuit" | "brique" | "encre" | "sable" | "danger";

const TONES: Record<Tone, string> = {
  or: "bg-or text-encre",
  nuit: "bg-nuit text-papier",
  brique: "bg-brique text-papier",
  encre: "bg-encre text-papier",
  sable: "bg-sable text-encre",
  danger: "bg-[#B3261E] text-papier",
};

export function Badge({ tone = "sable", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-pill px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide", TONES[tone], className)}>
      {children}
    </span>
  );
}
