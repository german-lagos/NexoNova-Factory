import type { Metadata } from "next";
import { site } from "../content";
import "../styles/tokens.css";
import "../styles/globals.css";
export const metadata: Metadata = {
  title: `${site.brand.name} · Vista previa`,
  description: site.hero.description,
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es-CL"><body>{children}</body></html>;
}
