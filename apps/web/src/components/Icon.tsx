import type { SVGProps } from "react";

/** Jeu d'icônes trait, cohérent (§7.3). Les émojis du prototype sont remplacés. */
const PATHS: Record<string, string> = {
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14Zm9 16-4.3-4.3",
  heart: "M12 20.5s-7.5-4.6-9.3-9.2A5 5 0 0 1 12 6.6a5 5 0 0 1 9.3 4.7C19.5 15.9 12 20.5 12 20.5Z",
  pin: "M12 21s6-5.6 6-11a6 6 0 1 0-12 0c0 5.4 6 11 6 11Zm0-8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
  calendar: "M7 3v3m10-3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-14v5l3 2",
  ticket: "M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 1 0 0 4v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 1 0 0-4V8Zm6-2v12",
  share: "M12 3v12m0-12-4 4m4-4 4 4M5 13v6a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-6",
  globe: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-9-9h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18",
  check: "m5 12 5 5L20 7",
  x: "M6 6l12 12M18 6 6 18",
  menu: "M4 7h16M4 12h16M4 17h16",
  arrow: "M5 12h14m-6-6 6 6-6 6",
  wheelchair: "M9 5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm-1 3v6h6l3 5m-9-5a5 5 0 1 0 7 6M8 8h5",
  star: "m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9L12 3Z",
  flag: "M5 21V4m0 0h13l-2.5 4L18 12H5",
  download: "M12 3v12m0 0-4-4m4 4 4-4M5 21h14",
  plus: "M12 5v14M5 12h14",
  spark: "M12 3v4m0 10v4M3 12h4m10 0h4m-3.6-6.4-2.8 2.8M9.4 14.6l-2.8 2.8m0-10.8 2.8 2.8m5.2 5.2 2.8 2.8",
};

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20, ...props }: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d={PATHS[name]} />
    </svg>
  );
}
