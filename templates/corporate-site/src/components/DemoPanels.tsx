import s from "./Site.module.css";
export function DemoPanels() {
  return <section id="consulta" className={s.section} aria-labelledby="inquiry-title"><div className={`${s.container} ${s.demoGrid}`}>
    <article className={s.plan}><p className={s.eyebrow}>Sin pedidos ni contratación</p><h2 id="inquiry-title">Tu consulta</h2>
      <p>Este espacio reunirá tus intereses para preparar una consulta local.</p>
      <p>No se ha enviado ninguna consulta.</p><button className={s.button} type="button" disabled>Preparar · Próximamente</button>
    </article>
    <article className={s.chat} aria-labelledby="chat-title"><header><span aria-hidden="true">✦</span><h2 id="chat-title">Asistente de demostración</h2></header>
      <p>Vista previa del asistente local. Las respuestas de demostración estarán disponibles en una próxima etapa.</p>
      <label htmlFor="chat-message">Mensaje</label><input id="chat-message" placeholder="Escribe tu consulta" disabled />
      <button className={s.button} type="button" disabled>Enviar · No habilitado</button>
    </article>
  </div></section>;
}
