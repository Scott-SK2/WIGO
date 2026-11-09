import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Tout sauf les fichiers statiques, l'API Next et les assets PWA
  matcher: ["/((?!api|_next|_vercel|icons|.*\\..*).*)"],
};
