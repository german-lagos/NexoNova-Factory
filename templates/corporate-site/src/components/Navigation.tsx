import s from "./Site.module.css";
const Links = ({ hasPlans }: { hasPlans: boolean }) => <>
  <a href="#inicio">Inicio</a><a href="#sobre-nosotros">Nosotros</a>
  {hasPlans && <a href="#planes">Planes demo</a>}<a href="#servicios">Servicios</a>
  <a href="#preguntas">FAQ</a><a href="#contacto">Contacto</a>
</>;
export function Header({ brand, hasPlans }: { brand: string; hasPlans: boolean }) {
  return <header className={s.header}><div className={s.headerInner}>
    <a className={s.wordmark} href="#inicio" aria-label={`${brand}, inicio`}>{brand}</a>
    <nav className={s.desktopNav} aria-label="Principal"><Links hasPlans={hasPlans} /></nav>
    <a className={s.inquiryLink} href="#consulta">Tu consulta <span aria-hidden="true">↗</span></a>
    <details className={s.mobileNav}><summary>Menú</summary>
      <nav aria-label="Principal móvil"><Links hasPlans={hasPlans} /></nav>
    </details>
  </div></header>;
}
export function Footer({ brand }: { brand: string }) {
  return <footer className={s.footer}><div className={s.container}>
    <a className={s.wordmark} href="#inicio">{brand}</a>
    <p>Piloto interno · Contenido provisional · Sin contratación ni envío de consultas.</p>
    <a href="#contacto">Contacto</a>
  </div></footer>;
}
