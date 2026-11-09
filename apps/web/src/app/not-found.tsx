import Link from "next/link";

import "./globals.css";

export default function RootNotFound() {
  return (
    <html lang="fr">
      <body className="grid min-h-screen place-items-center bg-papier p-6 text-center">
        <div>
          <h1 className="font-display text-3xl font-black text-brique">WIGO</h1>
          <p className="mt-2 text-gris">Page introuvable · Pagina niet gevonden · Page not found</p>
          <Link href="/fr" className="btn-primary mt-6">Accueil</Link>
        </div>
      </body>
    </html>
  );
}
