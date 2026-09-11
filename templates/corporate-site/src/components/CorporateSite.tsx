import type { CSSProperties } from "react";
import type { SiteContent } from "../content/types";
import { Header, Footer } from "./Navigation";
import { Hero, About, Plans, Services, FAQ, Contact } from "./Sections";
import { DemoPanels } from "./DemoPanels";
import s from "./Site.module.css";
export function CorporateSite({ content }: { content: SiteContent }) {
  const tokens = { "--brand-navy": content.brand.navy, "--brand-blue": content.brand.blue,
    "--brand-cyan": content.brand.cyan } as CSSProperties;
  return <div className={s.site} style={tokens}>
    <a className={s.skip} href="#contenido">Saltar al contenido</a>
    <Header brand={content.brand.name} hasPlans={content.plans.length > 0} />
    <main id="contenido">
      <Hero content={content.hero} />
      <About content={content.about} />
      {content.plans.length > 0 && <Plans plans={content.plans} />}
      <Services services={content.services} />
      <FAQ entries={content.faq} />
      <Contact />
      <DemoPanels />
    </main>
    <Footer brand={content.brand.name} />
  </div>;
}
