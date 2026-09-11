import type { SiteContent } from "../content/types";
import s from "./Site.module.css";
export function Hero({ content }: { content: SiteContent["hero"] }) {
  return <section id="inicio" className={s.hero}><div className={`${s.container} ${s.heroGrid}`}>
    <div><p className={s.eyebrow}>Vista previa · Contenido provisional</p>
      <h1>{content.title}<br /><span>{content.accent}</span></h1><p>{content.description}</p>
      <a className={s.lightButton} href="#contacto">Hablemos de tu proyecto <span aria-hidden="true">→</span></a>
    </div>
    <section id="dominios" className={s.domain} aria-labelledby="domain-title">
      <p className={s.eyebrow}>Demostración local</p><h2 id="domain-title">Consulta tu dominio</h2>
      <p>Una idea para tu próxima dirección online.</p>
      <label htmlFor="domain">Nombre de dominio</label>
      <div className={s.search}><span aria-hidden="true">www.</span><input id="domain" placeholder="tudominio.cl" disabled /><button type="button" disabled>Consultar</button></div>
      <p className={s.note}>Vista visual: consulta aún no habilitada. No se comprueba disponibilidad ni se registra ningún dominio.</p>
      <a href="#consulta">Ya tengo un dominio <span aria-hidden="true">→</span></a>
    </section>
  </div></section>;
}
export function About({ content }: { content: SiteContent["about"] }) {
  return <section id="sobre-nosotros" className={s.section}><div className={s.container}>
    <div className={s.about}><p className={s.eyebrow}>Sobre nosotros</p><h2>{content.title}</h2><p>{content.description}</p></div>
  </div></section>;
}
export function Plans({ plans }: { plans: SiteContent["plans"] }) {
  return <section id="planes" className={`${s.section} ${s.soft}`}><div className={s.container}>
    <p className={s.eyebrow}>Opciones para conversar</p><h2>Un punto de partida para tu proyecto.</h2>
    <p>Precios demostrativos en CLP. No constituyen una oferta comercial.</p>
    <div className={s.planGrid}>{plans.map(plan => <article className={s.plan} key={plan.id}>
      <span className={s.badge}>Ejemplo provisional</span><h3>{plan.name}</h3><p className={s.price}>{plan.price}</p>
      <p>{plan.description}</p><a className={s.button} href="#consulta">Consultar sobre este plan</a>
    </article>)}</div>
  </div></section>;
}
export function Services({ services }: { services: SiteContent["services"] }) {
  return <section id="servicios" className={s.section}><div className={s.container}>
    <p className={s.eyebrow}>Servicios</p><h2>Tu próxima web empieza aquí.</h2>
    <div className={s.bento}>{services.map((service, i) => <article className={s.service} key={service.title}>
      <span className={s.serviceIndex} aria-hidden="true">0{i + 1} ↗</span><h3>{service.title}</h3><p>{service.description}</p>
      <a href="#contacto">Conversemos <span aria-hidden="true">→</span></a>
    </article>)}</div>
  </div></section>;
}
export function FAQ({ entries }: { entries: SiteContent["faq"] }) {
  return <section id="preguntas" className={`${s.section} ${s.soft}`}><div className={`${s.container} ${s.faq}`}>
    <div><p className={s.eyebrow}>Resolvamos tus dudas</p><h2>Preguntas frecuentes.</h2></div>
    <div>{entries.map(entry => <details className={s.faqItem} key={entry.question}>
      <summary>{entry.question}</summary><p>{entry.answer}</p>
    </details>)}</div>
  </div></section>;
}
export function Contact() {
  return <section id="contacto" className={s.contact}><div className={s.container}>
    <h2>Tu próximo paso online empieza con una conversación.</h2>
    <a className={s.button} href="#consulta">Preparar una consulta <span aria-hidden="true">→</span></a>
    <p>Vista previa: la preparación local todavía no está habilitada. No se ha enviado ninguna consulta.</p>
  </div></section>;
}
