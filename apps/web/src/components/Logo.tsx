import clsx from "clsx";

/** Logo rond « WIGO » sur fond brique (§7.3). */
export function Logo({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <span
      className={clsx("relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brique bg-rings font-display font-black uppercase tracking-tight text-papier", className)}
      style={{ width: size, height: size, fontSize: size * 0.32 }}
      aria-hidden="true"
    >
      WIGO
    </span>
  );
}
