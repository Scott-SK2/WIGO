import type { ReactNode } from "react";

import { Logo } from "./Logo";

export function EmptyState({ title, text, children }: { title: string; text?: string; children?: ReactNode }) {
  return (
    <div className="panel flex flex-col items-center text-center">
      <Logo size={56} className="opacity-80" />
      <h2 className="mt-4 font-display text-2xl font-extrabold">{title}</h2>
      {text && <p className="mt-2 max-w-md text-gris">{text}</p>}
      {children && <div className="mt-5 flex flex-wrap justify-center gap-2">{children}</div>}
    </div>
  );
}
