# Especificación ERP Web Pequeño

A continuación tienes una **especificación directa** para un ERP web pequeño, coherente entre módulos, tablas y endpoints.

# 0. Supuesto general del sistema

Sistema ERP web para gestionar:

Clientes, productos, inventario, ventas, devoluciones, compras, producción, facturación, reportes, dashboard y alertas por correo.

Arquitectura recomendada:

`/api/v1`

Regla general de endpoints:

`GET` consulta, `POST` crea, `PUT/PATCH` actualiza, `DELETE` elimina lógico, endpoints de acción solo para cambios de estado.

Ejemplo correcto:

`POST /api/v1/sales-orders/{id}/confirm`

No recomendado:

`POST /api/v1/confirmarVenta`

---

# A. Casos de uso con flujos

## 1. Gestión de clientes

### UC-CLI-01 Registrar cliente

Actor: Usuario ventas / administrador.

Flujo:

1. Usuario abre módulo Clientes.
2. Selecciona Nuevo cliente.
3. Ingresa datos comerciales, tributarios, contacto y condiciones.
4. Sistema valida datos obligatorios y duplicados.
5. Sistema guarda cliente en estado Activo.
6. Sistema registra auditoría.

Alternos:

- Si el documento tributario ya existe, bloquea guardado.
- Si faltan datos obligatorios, muestra errores.
- Si el usuario no tiene permiso, deniega operación.

### UC-CLI-02 Editar cliente

Flujo:

1. Usuario busca cliente.
2. Abre ficha.
3. Modifica datos permitidos.
4. Sistema valida cambios.
5. Sistema actualiza registro.
6. Sistema guarda historial.

Alternos:

- No permite cambiar documento tributario si tiene facturas emitidas, salvo rol autorizado.
- No permite editar clientes eliminados.

### UC-CLI-03 Consultar cliente

Flujo:

1. Usuario ingresa filtro: nombre, documento, correo, estado.
2. Sistema muestra listado paginado.
3. Usuario abre detalle.
4. Sistema muestra datos, contactos, ventas, deuda, devoluciones y facturas.

Alternos:

- Si no hay resultados, muestra listado vacío.
- Si no tiene permiso financiero, oculta deuda y crédito.

### UC-CLI-04 Gestionar crédito de cliente

Flujo:

1. Usuario abre pestaña Crédito.
2. Define límite de crédito, plazo de pago y bloqueo.
3. Sistema valida permisos.
4. Sistema guarda condiciones.
5. Sistema aplica reglas en ventas y facturación.

Alternos:

- Si el cliente tiene deuda vencida, puede quedar bloqueado.
- Si supera límite de crédito, ventas futuras requieren autorización.

### UC-CLI-05 Inactivar cliente

Flujo:

1. Usuario selecciona cliente.
2. Presiona Inactivar.
3. Sistema valida que no existan operaciones abiertas críticas.
4. Sistema cambia estado a Inactivo.
5. Sistema registra auditoría.

Alternos:

- No se puede inactivar si tiene ventas pendientes de despacho.
- Cliente inactivo no puede usarse en nuevas ventas.

---

## 2. Gestión de productos e inventario

### UC-INV-01 Registrar producto

Flujo:

1. Usuario abre Productos.
2. Selecciona Nuevo producto.
3. Ingresa SKU, nombre, categoría, unidad, precio, costo, impuestos y control de stock.
4. Sistema valida SKU único.
5. Sistema guarda producto activo.

Alternos:

- Si el producto controla inventario, exige unidad y bodega inicial opcional.
- Si no controla inventario, no genera stock.

### UC-INV-02 Editar producto

Flujo:

1. Usuario busca producto.
2. Abre ficha.
3. Modifica datos permitidos.
4. Sistema valida dependencias.
5. Sistema actualiza producto.

Alternos:

- No permite cambiar unidad base si tiene movimientos.
- No permite eliminar producto usado en ventas, compras o producción.

### UC-INV-03 Registrar movimiento de inventario

Flujo:

1. Usuario abre Movimientos.
2. Selecciona tipo: entrada, salida, ajuste, transferencia, producción.
3. Ingresa producto, bodega, cantidad y motivo.
4. Sistema valida stock disponible si es salida.
5. Sistema registra movimiento.
6. Sistema recalcula stock.

Alternos:

- Si stock queda negativo y no está permitido, bloquea.
- Si producto no controla stock, bloquea movimiento.

### UC-INV-04 Transferir stock entre bodegas

Flujo:

1. Usuario selecciona producto y bodega origen.
2. Ingresa bodega destino y cantidad.
3. Sistema valida stock disponible.
4. Sistema registra salida en origen.
5. Sistema registra entrada en destino.
6. Sistema actualiza saldos.

Alternos:

- No permite origen y destino iguales.
- No permite transferir productos inactivos.

### UC-INV-05 Ajustar inventario

Flujo:

1. Usuario abre Ajustes.
2. Selecciona producto, bodega, cantidad real y motivo.
3. Sistema calcula diferencia.
4. Usuario confirma.
5. Sistema crea movimiento de ajuste.
6. Sistema actualiza stock.

Alternos:

- Ajustes mayores al umbral requieren aprobación.
- Motivo obligatorio.

### UC-INV-06 Conteo físico

Flujo:

1. Usuario crea conteo por bodega.
2. Sistema congela listado de productos a contar.
3. Usuario ingresa cantidades físicas.
4. Sistema calcula diferencias.
5. Supervisor aprueba diferencias.
6. Sistema genera movimientos de ajuste.

Alternos:

- No permite cerrar conteo con líneas pendientes.
- No permite modificar conteo cerrado.

---

## 3. Gestión de ventas

### UC-VTA-01 Crear cotización

Flujo:

1. Usuario selecciona cliente.
2. Agrega productos, cantidades, descuentos e impuestos.
3. Sistema calcula total.
4. Usuario guarda cotización.
5. Sistema deja estado Borrador o Emitida.

Alternos:

- No permite productos inactivos.
- Descuento sobre límite requiere autorización.

### UC-VTA-02 Convertir cotización en orden de venta

Flujo:

1. Usuario abre cotización emitida.
2. Selecciona Convertir a venta.
3. Sistema valida cliente, precios, stock y vigencia.
4. Sistema crea orden de venta.
5. Sistema relaciona documentos.

Alternos:

- Si cotización venció, bloquea conversión.
- Si stock insuficiente, permite pedido pendiente solo si la empresa lo permite.

### UC-VTA-03 Registrar venta directa

Flujo:

1. Usuario abre Nueva venta.
2. Selecciona cliente.
3. Agrega productos.
4. Sistema valida stock, crédito y precios.
5. Usuario confirma.
6. Sistema descuenta o reserva stock según configuración.
7. Sistema genera documento pendiente de facturación o factura directa.

Alternos:

- Cliente bloqueado por crédito requiere autorización.
- Producto sin stock bloquea o deja pendiente según regla.

### UC-VTA-04 Despachar venta

Flujo:

1. Usuario abre orden confirmada.
2. Selecciona productos a despachar.
3. Sistema valida stock disponible.
4. Usuario confirma despacho.
5. Sistema genera salida de inventario.
6. Orden queda parcial o despachada.

Alternos:

- Si despacho parcial está deshabilitado, exige completar toda la orden.
- Si falta stock, bloquea despacho.

### UC-VTA-05 Anular venta

Flujo:

1. Usuario abre venta.
2. Selecciona Anular.
3. Ingresa motivo.
4. Sistema valida estado.
5. Sistema revierte reservas o movimientos permitidos.
6. Sistema marca venta como Anulada.

Alternos:

- Venta facturada requiere nota de crédito.
- Venta despachada requiere devolución antes de anular.

---

## 4. Gestión de devoluciones

### UC-DEV-01 Crear solicitud de devolución

Flujo:

1. Usuario busca venta original.
2. Selecciona productos a devolver.
3. Ingresa cantidad y motivo.
4. Sistema valida plazo, cantidad y estado.
5. Sistema crea devolución en estado Solicitada.

Alternos:

- No permite devolver más de lo vendido.
- No permite devolver productos ya devueltos completamente.

### UC-DEV-02 Aprobar devolución

Flujo:

1. Supervisor abre devolución solicitada.
2. Revisa motivo, venta y producto.
3. Aprueba o rechaza.
4. Sistema registra decisión.

Alternos:

- Rechazo exige motivo.
- Aprobación puede exigir inspección física.

### UC-DEV-03 Recibir productos devueltos

Flujo:

1. Usuario abre devolución aprobada.
2. Registra productos recibidos.
3. Indica condición: apto, dañado, merma, revisión.
4. Sistema genera movimiento de inventario si corresponde.
5. Sistema actualiza devolución.

Alternos:

- Producto dañado no vuelve a stock vendible.
- Recepción parcial deja devolución pendiente.

### UC-DEV-04 Generar nota de crédito

Flujo:

1. Usuario abre devolución recibida.
2. Selecciona generar nota de crédito.
3. Sistema calcula monto.
4. Sistema valida factura original.
5. Sistema emite nota.
6. Sistema cierra devolución.

Alternos:

- Si venta no fue facturada, genera saldo a favor o reverso interno.
- Si monto no coincide, requiere autorización.

### UC-DEV-05 Rechazar devolución

Flujo:

1. Usuario abre solicitud.
2. Ingresa motivo de rechazo.
3. Sistema cambia estado a Rechazada.
4. Sistema notifica al cliente si aplica.

Alternos:

- No permite rechazar devolución ya recibida.
- No permite editar rechazo sin permiso.

---

## 5. Gestión de compras

### UC-COM-01 Registrar proveedor

Flujo:

1. Usuario abre Proveedores.
2. Ingresa datos tributarios, comerciales y contacto.
3. Sistema valida duplicados.
4. Sistema guarda proveedor activo.

Alternos:

- Documento tributario duplicado bloquea guardado.
- Proveedor incompleto queda en estado Borrador si la configuración lo permite.

### UC-COM-02 Crear orden de compra

Flujo:

1. Usuario selecciona proveedor.
2. Agrega productos, cantidades, precios y fechas.
3. Sistema calcula total.
4. Usuario guarda orden.
5. Sistema deja estado Borrador o Emitida.

Alternos:

- Producto inactivo bloquea línea.
- Precio bajo cero bloquea operación.

### UC-COM-03 Aprobar orden de compra

Flujo:

1. Supervisor revisa orden.
2. Sistema valida monto y presupuesto.
3. Supervisor aprueba.
4. Sistema cambia estado a Aprobada.

Alternos:

- Si supera monto máximo, requiere aprobación superior.
- Si proveedor bloqueado, no permite aprobar.

### UC-COM-04 Recibir mercadería

Flujo:

1. Usuario abre orden aprobada.
2. Ingresa cantidades recibidas.
3. Sistema valida cantidades pendientes.
4. Sistema registra recepción.
5. Sistema genera entrada de inventario.
6. Orden queda parcial o recibida.

Alternos:

- Cantidad recibida mayor a orden requiere tolerancia o autorización.
- Producto sin control de stock no genera movimiento.

### UC-COM-05 Registrar factura de compra

Flujo:

1. Usuario abre recepción u orden.
2. Ingresa número de factura, fecha, neto, impuesto y total.
3. Sistema valida proveedor y montos.
4. Sistema registra factura.
5. Sistema genera cuenta por pagar.

Alternos:

- Factura duplicada del mismo proveedor bloquea.
- Diferencias con orden requieren revisión.

---

## 6. Gestión de producción

### UC-PROD-01 Crear receta o lista de materiales

Flujo:

1. Usuario selecciona producto terminado.
2. Agrega insumos y cantidades.
3. Sistema valida unidades y productos activos.
4. Sistema guarda versión de receta.

Alternos:

- No permite producto terminado como insumo de sí mismo.
- Cambios en receta usada generan nueva versión.

### UC-PROD-02 Crear orden de producción

Flujo:

1. Usuario selecciona producto terminado.
2. Ingresa cantidad a producir y fecha requerida.
3. Sistema carga receta vigente.
4. Sistema calcula insumos requeridos.
5. Sistema crea orden en estado Planificada.

Alternos:

- Sin receta activa, bloquea creación.
- Stock insuficiente de insumos muestra alerta.

### UC-PROD-03 Liberar insumos

Flujo:

1. Usuario abre orden planificada.
2. Solicita liberar materiales.
3. Sistema valida stock de insumos.
4. Sistema descuenta inventario.
5. Orden queda En proceso.

Alternos:

- Stock insuficiente bloquea o genera requerimiento de compra.
- Insumo alternativo requiere autorización.

### UC-PROD-04 Registrar producción

Flujo:

1. Usuario abre orden en proceso.
2. Ingresa cantidad producida, merma y observaciones.
3. Sistema valida cantidad.
4. Sistema ingresa producto terminado a inventario.
5. Sistema actualiza avance.

Alternos:

- Producción mayor a orden requiere tolerancia.
- Merma superior a umbral requiere motivo.

### UC-PROD-05 Cerrar orden de producción

Flujo:

1. Usuario revisa consumos y producción.
2. Sistema valida diferencias.
3. Usuario cierra orden.
4. Sistema bloquea nuevos movimientos.
5. Sistema calcula costo real.

Alternos:

- No permite cerrar con insumos pendientes.
- No permite cerrar con cantidades negativas.

---

## 7. Gestión de facturación

### UC-FAC-01 Emitir factura de venta

Flujo:

1. Usuario abre venta facturable.
2. Sistema carga cliente, productos, impuestos y total.
3. Usuario confirma emisión.
4. Sistema genera factura.
5. Sistema cambia venta a Facturada.
6. Sistema registra cuenta por cobrar.

Alternos:

- Venta anulada no puede facturarse.
- Cliente sin datos fiscales válidos bloquea emisión.

### UC-FAC-02 Emitir nota de crédito

Flujo:

1. Usuario selecciona factura.
2. Indica motivo: devolución, descuento, anulación, corrección.
3. Sistema calcula monto.
4. Usuario confirma.
5. Sistema emite nota y actualiza saldo.

Alternos:

- Monto no puede superar saldo facturado disponible.
- Factura anulada no permite nota.

### UC-FAC-03 Emitir nota de débito

Flujo:

1. Usuario selecciona factura.
2. Ingresa concepto y monto adicional.
3. Sistema calcula impuestos.
4. Usuario confirma.
5. Sistema emite nota de débito.

Alternos:

- Concepto obligatorio.
- Monto debe ser mayor a cero.

### UC-FAC-04 Registrar pago de factura

Flujo:

1. Usuario abre factura pendiente.
2. Ingresa medio de pago, fecha y monto.
3. Sistema valida saldo.
4. Sistema registra pago.
5. Sistema actualiza estado: parcial o pagada.

Alternos:

- Monto mayor al saldo requiere manejo de anticipo.
- Factura anulada no admite pago.

### UC-FAC-05 Anular documento tributario

Flujo:

1. Usuario abre documento.
2. Selecciona Anular.
3. Ingresa motivo.
4. Sistema valida estado y permisos.
5. Sistema anula o genera documento correctivo.
6. Sistema registra auditoría.

Alternos:

- Documento informado externamente puede requerir nota de crédito.
- Documento pagado requiere reverso de pago.

---

## 8. Gestión de reportes y dashboard

### UC-REP-01 Ver dashboard general

Flujo:

1. Usuario ingresa al sistema.
2. Sistema carga indicadores según permisos.
3. Muestra ventas, compras, inventario, producción, facturación y alertas.
4. Usuario filtra por fecha, sucursal o bodega.

Alternos:

- Si no tiene permisos, oculta indicadores sensibles.
- Si no hay datos, muestra indicadores en cero.

### UC-REP-02 Consultar reporte de ventas

Flujo:

1. Usuario abre Reportes.
2. Selecciona Ventas.
3. Define rango de fechas y filtros.
4. Sistema genera resultados.
5. Usuario exporta si tiene permiso.

Alternos:

- Rango demasiado grande requiere ejecución diferida.
- Exportación queda registrada.

### UC-REP-03 Consultar reporte de inventario

Flujo:

1. Usuario selecciona reporte de stock.
2. Filtra por producto, categoría, bodega y estado.
3. Sistema muestra stock, costo y valorización.
4. Usuario exporta.

Alternos:

- Usuario sin permiso de costos solo ve cantidades.
- Stock negativo se resalta.

### UC-REP-04 Consultar reporte de producción

Flujo:

1. Usuario filtra órdenes por fecha, estado y producto.
2. Sistema muestra cantidades producidas, mermas y costos.
3. Usuario abre detalle.
4. Sistema muestra insumos consumidos.

Alternos:

- Orden cerrada solo lectura.
- Costos ocultos según permiso.

### UC-REP-05 Configurar dashboard

Flujo:

1. Usuario abre configuración.
2. Selecciona widgets visibles.
3. Define filtros por defecto.
4. Sistema guarda preferencias por usuario.

Alternos:

- Widgets no autorizados no aparecen.
- Cambios aplican al próximo ingreso o recarga.

---

## 9. Gestión de alertas por correo

### UC-ALT-01 Configurar alerta

Flujo:

1. Usuario abre Alertas.
2. Selecciona tipo de alerta.
3. Define condición, frecuencia y destinatarios.
4. Sistema valida correos.
5. Sistema guarda alerta activa.

Alternos:

- No permite alerta sin destinatarios.
- No permite frecuencia inválida.

### UC-ALT-02 Enviar alerta de stock bajo

Flujo:

1. Sistema ejecuta proceso programado.
2. Consulta productos bajo stock mínimo.
3. Genera lista por bodega.
4. Envía correo a responsables.
5. Registra envío.

Alternos:

- Si no hay productos bajo mínimo, no envía.
- Si falla correo, registra error y reintenta.

### UC-ALT-03 Enviar alerta de facturas vencidas

Flujo:

1. Sistema identifica facturas vencidas.
2. Agrupa por responsable o cliente.
3. Envía correo.
4. Registra fecha de notificación.

Alternos:

- No alerta facturas anuladas o pagadas.
- Evita duplicar alertas dentro de la misma frecuencia.

### UC-ALT-04 Enviar alerta de órdenes de producción atrasadas

Flujo:

1. Sistema consulta órdenes con fecha comprometida vencida.
2. Valida estado distinto de Cerrada o Anulada.
3. Envía correo a producción.
4. Registra alerta.

Alternos:

- Orden reprogramada actualiza fecha base.
- Orden cerrada queda fuera.

### UC-ALT-05 Reintentar correos fallidos

Flujo:

1. Sistema consulta correos en estado Fallido.
2. Valida número de intentos.
3. Reintenta envío.
4. Actualiza estado.

Alternos:

- Si supera máximo de intentos, queda en Error definitivo.
- Error de destinatario inválido no se reintenta.

---

# B. Especificación de pantallas

## 40 pantallas

### P-01 Login

Campos: correo, contraseña.  
Acciones: ingresar, recuperar contraseña.  
Validaciones: credenciales, usuario activo.

### P-02 Recuperar contraseña

Campos: correo.  
Acciones: enviar enlace.  
Validaciones: correo válido.

### P-03 Dashboard general

Muestra: ventas del día, ventas del mes, stock crítico, facturas vencidas, compras pendientes, producción atrasada.  
Acciones: filtrar, abrir detalle.

### P-04 Listado de clientes

Campos filtro: nombre, documento, correo, estado.  
Acciones: buscar, crear, exportar, abrir detalle.

### P-05 Formulario de cliente

Campos: razón social, documento, giro, correo, teléfono, dirección, condición de pago, límite de crédito.  
Acciones: guardar, cancelar.

### P-06 Detalle de cliente

Muestra: datos generales, ventas, facturas, pagos, devoluciones, crédito.  
Acciones: editar, inactivar.

### P-07 Contactos de cliente

Campos: nombre, cargo, correo, teléfono, principal.  
Acciones: agregar, editar, eliminar.

### P-08 Crédito de cliente

Campos: límite, plazo, estado crédito, motivo bloqueo.  
Acciones: actualizar, bloquear, desbloquear.

### P-09 Listado de productos

Filtros: SKU, nombre, categoría, estado, controla stock.  
Acciones: crear, editar, exportar.

### P-10 Formulario de producto

Campos: SKU, nombre, descripción, categoría, unidad, costo, precio, impuesto, stock mínimo.  
Acciones: guardar.

### P-11 Categorías y unidades

Campos: categoría, unidad, símbolo, estado.  
Acciones: crear, editar, inactivar.

### P-12 Consulta de stock

Filtros: producto, bodega, ubicación, categoría.  
Muestra: disponible, reservado, comprometido, mínimo.

### P-13 Movimientos de inventario

Filtros: fecha, producto, bodega, tipo.  
Acciones: consultar, exportar, abrir documento origen.

### P-14 Ajuste de inventario

Campos: producto, bodega, cantidad real, motivo.  
Acciones: calcular diferencia, confirmar.

### P-15 Transferencia de stock

Campos: producto, bodega origen, bodega destino, cantidad.  
Acciones: transferir.

### P-16 Conteo físico

Campos: bodega, fecha, responsable, líneas de conteo.  
Acciones: iniciar, cargar conteo, aprobar, cerrar.

### P-17 Bodegas y ubicaciones

Campos: nombre bodega, código, ubicación física, estado.  
Acciones: crear, editar, inactivar.

### P-18 Cotizaciones

Filtros: cliente, fecha, estado.  
Acciones: crear, enviar, convertir a venta.

### P-19 Formulario de venta

Campos: cliente, productos, cantidades, descuentos, impuestos, total, condición de pago.  
Acciones: guardar, confirmar, facturar.

### P-20 Venta rápida / POS

Campos: cliente, producto, cantidad, medio de pago.  
Acciones: cobrar, emitir comprobante.

### P-21 Despacho de venta

Campos: orden, bodega, productos, cantidades.  
Acciones: despachar total, despacho parcial.

### P-22 Pagos de venta

Campos: factura, monto, fecha, medio de pago, referencia.  
Acciones: registrar pago.

### P-23 Solicitud de devolución

Campos: venta, producto, cantidad, motivo.  
Acciones: solicitar, aprobar, rechazar.

### P-24 Recepción de devolución

Campos: devolución, producto, cantidad recibida, condición.  
Acciones: recibir, enviar a stock, marcar merma.

### P-25 Proveedores

Filtros: razón social, documento, correo, estado.  
Acciones: crear, editar, inactivar.

### P-26 Formulario de proveedor

Campos: razón social, documento, contacto, correo, teléfono, dirección, condición de pago.  
Acciones: guardar.

### P-27 Órdenes de compra

Filtros: proveedor, fecha, estado.  
Acciones: crear, aprobar, anular, recibir.

### P-28 Formulario de orden de compra

Campos: proveedor, productos, cantidades, precios, fecha requerida.  
Acciones: guardar, emitir, aprobar.

### P-29 Recepción de compra

Campos: orden de compra, productos, cantidades recibidas, bodega.  
Acciones: recibir parcial, recibir total.

### P-30 Factura de compra

Campos: proveedor, número factura, fecha, neto, impuesto, total.  
Acciones: registrar, asociar a recepción.

### P-31 Recetas / BOM

Campos: producto terminado, versión, insumos, cantidades, merma estándar.  
Acciones: crear versión, activar, inactivar.

### P-32 Órdenes de producción

Filtros: producto, fecha, estado.  
Acciones: crear, liberar, cerrar.

### P-33 Consumo de producción

Campos: orden, insumos, cantidad requerida, cantidad consumida.  
Acciones: consumir, ajustar consumo.

### P-34 Reporte de producción

Campos: orden, cantidad producida, merma, bodega destino.  
Acciones: registrar producción.

### P-35 Facturación

Filtros: cliente, fecha, estado, tipo documento.  
Acciones: emitir factura, nota de crédito, nota de débito, anular.

### P-36 Reportes

Muestra: ventas, compras, inventario, producción, facturación, clientes.  
Acciones: filtrar, exportar XLSX/PDF.

### P-37 Configuración de dashboard

Campos: widgets, orden, filtros por defecto.  
Acciones: guardar preferencias.

### P-38 Alertas por correo

Campos: tipo alerta, condición, frecuencia, destinatarios, estado.  
Acciones: crear, editar, activar, pausar.

### P-39 Usuarios y roles

Campos: usuario, correo, rol, estado.  
Acciones: crear usuario, asignar rol, bloquear.

### P-40 Auditoría

Filtros: usuario, módulo, acción, fecha.  
Muestra: acción, datos previos, datos nuevos, IP, fecha.

---

# C. Reglas de negocio

## 100 reglas de negocio

1. Todo registro operativo debe pertenecer a una empresa.
2. Todo usuario debe operar con un rol asignado.
3. Todo cambio crítico debe registrar auditoría.
4. Los registros usados en documentos no se eliminan físicamente.
5. La eliminación lógica cambia estado a Inactivo o Anulado.
6. Solo usuarios autorizados pueden ver costos.
7. Solo usuarios autorizados pueden modificar precios manualmente.
8. Solo usuarios autorizados pueden aprobar descuentos especiales.
9. Las fechas de documentos no pueden ser futuras salvo configuración.
10. La moneda base de la empresa se define en configuración.
11. El documento tributario del cliente debe ser único por empresa.
12. Un cliente inactivo no puede usarse en nuevas ventas.
13. Un cliente bloqueado por crédito no puede facturarse sin autorización.
14. El límite de crédito se evalúa contra facturas pendientes.
15. La deuda vencida puede bloquear nuevas ventas.
16. La condición de pago del cliente se copia a la venta.
17. El cliente genérico solo puede usarse en venta rápida.
18. Un cliente con facturas no puede eliminarse físicamente.
19. El contacto principal del cliente debe ser único.
20. El correo de facturación del cliente se usa para envío de documentos.
21. El SKU debe ser único por empresa.
22. Un producto inactivo no puede venderse ni comprarse.
23. Un producto sin control de stock no genera movimientos de inventario.
24. Un producto con control de stock requiere unidad base.
25. La unidad base no puede cambiar si existen movimientos.
26. El stock disponible es stock físico menos reservado.
27. El stock reservado no puede superar el stock físico.
28. El sistema no permite stock negativo salvo configuración.
29. El stock mínimo genera alerta cuando disponible es menor o igual al mínimo.
30. Todo movimiento de inventario debe tener tipo y motivo.
31. Todo movimiento de inventario debe afectar una bodega.
32. Las transferencias generan salida y entrada relacionadas.
33. No se permite transferir entre la misma bodega.
34. Los ajustes de inventario requieren motivo.
35. Ajustes superiores al umbral requieren aprobación.
36. El conteo físico cerrado no puede modificarse.
37. Un producto con lote requiere lote en entradas y salidas.
38. Un producto con vencimiento requiere fecha de vencimiento en entrada.
39. Los productos vencidos no pueden venderse salvo autorización.
40. La valorización de inventario usa costo promedio, FIFO o estándar según configuración.
41. Toda venta debe tener cliente.
42. Toda venta debe tener al menos una línea.
43. Una línea de venta debe tener producto, cantidad y precio.
44. No se permite vender productos inactivos.
45. No se permite confirmar venta con total cero, salvo documento autorizado.
46. El descuento por línea no puede superar el máximo permitido.
47. El descuento global no puede superar el máximo permitido.
48. La venta confirmada reserva stock si la empresa trabaja con reserva.
49. La venta despachada descuenta stock.
50. Una venta anulada no puede despacharse.
51. Una venta anulada no puede facturarse.
52. Una venta facturada no puede editar sus líneas.
53. Una venta parcialmente despachada no puede eliminarse.
54. La venta puede quedar en estado parcial si admite despacho parcial.
55. La venta requiere autorización si supera crédito del cliente.
56. La cotización vencida no puede convertirse en venta.
57. La cotización convertida no puede volver a convertirse.
58. El precio de venta se toma de lista de precios vigente.
59. El vendedor responsable queda registrado en la venta.
60. Las ventas deben recalcular impuestos al confirmar.
61. Toda devolución debe estar asociada a una venta.
62. No se puede devolver más cantidad que la vendida.
63. No se puede devolver más cantidad que la despachada.
64. No se puede devolver una venta anulada.
65. La devolución requiere motivo.
66. La devolución fuera de plazo requiere autorización.
67. Una devolución aprobada puede generar entrada a inventario.
68. Producto devuelto dañado no vuelve a stock vendible.
69. Una devolución facturada debe generar nota de crédito.
70. Una devolución rechazada no afecta inventario ni saldos.
71. El documento tributario del proveedor debe ser único por empresa.
72. Un proveedor inactivo no puede recibir órdenes de compra.
73. Toda orden de compra debe tener proveedor.
74. Toda orden de compra debe tener al menos una línea.
75. Una orden de compra aprobada no puede editarse sin reabrir.
76. La recepción no puede superar la orden salvo tolerancia configurada.
77. La recepción parcial deja la orden en estado Parcial.
78. La recepción total deja la orden en estado Recibida.
79. La factura de compra debe asociarse a proveedor.
80. La factura de compra no puede duplicarse por proveedor y número.
81. Toda orden de producción debe tener producto terminado.
82. El producto terminado debe tener receta activa.
83. Una receta debe tener al menos un insumo.
84. Un producto no puede ser insumo de sí mismo en la misma receta.
85. La liberación de producción consume insumos.
86. El registro de producción ingresa producto terminado.
87. La merma debe registrarse separada de la producción buena.
88. Una orden cerrada no admite nuevos consumos.
89. Una orden anulada no afecta stock.
90. El costo real de producción se calcula al cerrar la orden.
91. Toda factura debe tener cliente.
92. Toda factura debe tener al menos una línea.
93. La factura debe cuadrar neto, impuestos y total.
94. Una factura pagada no puede anularse directamente sin reverso.
95. La nota de crédito debe estar asociada a factura original.
96. La nota de crédito no puede superar el saldo facturado.
97. La nota de débito debe tener concepto obligatorio.
98. El pago no puede superar el saldo salvo anticipo autorizado.
99. Una factura pagada queda cerrada financieramente.
100. Todo documento tributario debe tener folio o número interno único.

---

# D. Validaciones y CHECK

## 200 validaciones mínimas

1. V001: `company_id` obligatorio en tablas operativas.
2. V002: `created_at` obligatorio.
3. V003: `updated_at` obligatorio.
4. V004: `created_by` obligatorio en operaciones manuales.
5. V005: `status` obligatorio.
6. V006: `status IN ('active','inactive','draft','confirmed','cancelled','closed')` según entidad.
7. V007: IDs deben ser UUID o enteros positivos.
8. V008: Fechas deben usar zona horaria del sistema.
9. V009: No aceptar fechas con formato inválido.
10. V010: No aceptar texto con longitud mayor a la definida.
11. V011: Correos deben tener formato válido.
12. V012: Teléfonos deben tener longitud mínima configurada.
13. V013: Campos monetarios deben tener dos decimales.
14. V014: Montos no pueden ser `NaN`.
15. V015: Montos no pueden ser nulos si participan en totales.
16. V016: Cantidades deben ser numéricas.
17. V017: Cantidades no pueden ser `NaN`.
18. V018: Cantidades deben tener máximo 4 decimales.
19. V019: Usuario debe estar autenticado.
20. V020: Usuario debe estar activo.
21. V021: Correo de usuario único por empresa.
22. V022: Contraseña mínima de 8 caracteres.
23. V023: Contraseña debe almacenarse cifrada, nunca en texto plano.
24. V024: Usuario bloqueado no puede iniciar sesión.
25. V025: Rol obligatorio para usuario activo.
26. V026: Rol inactivo no puede asignarse.
27. V027: Permiso requerido para crear registros.
28. V028: Permiso requerido para editar registros.
29. V029: Permiso requerido para anular documentos.
30. V030: Permiso requerido para ver costos.
31. V031: Token expirado debe rechazarse.
32. V032: Refresh token revocado debe rechazarse.
33. V033: Sesión debe registrar IP.
34. V034: Intentos fallidos de login deben registrarse.
35. V035: Cambio de contraseña exige contraseña actual.
36. V036: Razón social obligatoria.
37. V037: Documento tributario obligatorio.
38. V038: Documento tributario único por empresa.
39. V039: Nombre comercial máximo 150 caracteres.
40. V040: Correo de facturación obligatorio si envío electrónico activo.
41. V041: Correo de facturación debe ser válido.
42. V042: Dirección obligatoria para facturación.
43. V043: Ciudad obligatoria si dirección existe.
44. V044: País obligatorio.
45. V045: Estado de cliente debe ser activo, inactivo o bloqueado.
46. V046: Límite de crédito debe ser mayor o igual a cero.
47. V047: Plazo de pago debe ser mayor o igual a cero.
48. V048: Cliente bloqueado requiere motivo de bloqueo.
49. V049: Contacto de cliente requiere nombre.
50. V050: Contacto de cliente requiere correo o teléfono.
51. V051: Solo un contacto principal por cliente.
52. V052: Cliente con ventas no puede eliminarse físicamente.
53. V053: Cliente inactivo no puede asignarse a venta nueva.
54. V054: Código interno de cliente único por empresa.
55. V055: Documento tributario no puede contener espacios iniciales o finales.
56. V056: Razón social del proveedor obligatoria.
57. V057: Documento tributario del proveedor obligatorio.
58. V058: Documento tributario del proveedor único por empresa.
59. V059: Correo proveedor debe ser válido.
60. V060: Proveedor activo requiere condición de pago.
61. V061: Proveedor inactivo no puede usarse en orden de compra.
62. V062: Contacto proveedor requiere nombre.
63. V063: Factura de proveedor requiere número.
64. V064: Número de factura de proveedor único por proveedor.
65. V065: Proveedor con órdenes no puede eliminarse físicamente.
66. V066: SKU obligatorio.
67. V067: SKU único por empresa.
68. V068: Nombre de producto obligatorio.
69. V069: Categoría obligatoria.
70. V070: Unidad base obligatoria.
71. V071: Precio de venta mayor o igual a cero.
72. V072: Costo mayor o igual a cero.
73. V073: Stock mínimo mayor o igual a cero.
74. V074: Producto activo requiere estado válido.
75. V075: Producto con inventario requiere `track_stock = true`.
76. V076: Producto sin inventario no permite stock mínimo obligatorio.
77. V077: Código de barras único si existe.
78. V078: Impuesto asignado debe estar activo.
79. V079: Producto inactivo no puede agregarse a venta.
80. V080: Producto inactivo no puede agregarse a compra.
81. V081: Producto terminado debe estar marcado como producible.
82. V082: Producto insumo debe estar marcado como comprable o inventariable.
83. V083: Unidad base no puede cambiar con movimientos existentes.
84. V084: SKU no puede tener espacios iniciales o finales.
85. V085: Nombre producto máximo 200 caracteres.
86. V086: Código de bodega obligatorio.
87. V087: Código de bodega único por empresa.
88. V088: Nombre de bodega obligatorio.
89. V089: Bodega inactiva no acepta movimientos.
90. V090: Ubicación debe pertenecer a la bodega indicada.
91. V091: Stock físico mayor o igual a cero salvo stock negativo permitido.
92. V092: Stock reservado mayor o igual a cero.
93. V093: Stock reservado menor o igual a stock físico.
94. V094: Movimiento requiere producto.
95. V095: Movimiento requiere bodega.
96. V096: Movimiento requiere tipo.
97. V097: Movimiento requiere cantidad mayor a cero.
98. V098: Movimiento de salida requiere stock disponible suficiente.
99. V099: Movimiento de ajuste requiere motivo.
100. V100: Transferencia requiere bodega origen.
101. V101: Transferencia requiere bodega destino.
102. V102: Bodega origen distinta de bodega destino.
103. V103: Conteo físico requiere bodega.
104. V104: Conteo físico cerrado no permite editar líneas.
105. V105: Conteo físico requiere responsable.
106. V106: Línea de conteo requiere producto.
107. V107: Cantidad contada mayor o igual a cero.
108. V108: Diferencia de conteo debe calcularse automáticamente.
109. V109: Ajuste por conteo requiere aprobación si supera umbral.
110. V110: Movimiento anulado no debe afectar saldo.
111. V111: Venta requiere cliente.
112. V112: Venta requiere fecha.
113. V113: Venta requiere vendedor.
114. V114: Venta requiere al menos una línea.
115. V115: Línea de venta requiere producto.
116. V116: Línea de venta requiere cantidad mayor a cero.
117. V117: Línea de venta requiere precio mayor o igual a cero.
118. V118: Descuento de línea mayor o igual a cero.
119. V119: Descuento de línea no puede superar subtotal de línea.
120. V120: Descuento global no puede superar subtotal del documento.
121. V121: Total venta mayor o igual a cero.
122. V122: Venta confirmada no permite editar cliente.
123. V123: Venta facturada no permite editar líneas.
124. V124: Venta anulada no permite despacho.
125. V125: Venta anulada no permite facturación.
126. V126: Cotización requiere fecha de vencimiento.
127. V127: Cotización vencida no puede convertirse.
128. V128: Orden de venta requiere estado válido.
129. V129: Despacho requiere venta confirmada.
130. V130: Despacho requiere bodega.
131. V131: Despacho requiere cantidad mayor a cero.
132. V132: Cantidad despachada no puede superar cantidad pendiente.
133. V133: Venta con crédito excedido requiere autorización.
134. V134: Producto sin stock bloquea confirmación si no se permite pendiente.
135. V135: Impuesto de venta debe recalcularse al guardar.
136. V136: Devolución requiere venta original.
137. V137: Devolución requiere cliente.
138. V138: Devolución requiere motivo.
139. V139: Línea de devolución requiere producto.
140. V140: Cantidad devuelta mayor a cero.
141. V141: Cantidad devuelta no puede superar cantidad vendida.
142. V142: Cantidad devuelta no puede superar cantidad despachada.
143. V143: No permitir devolución duplicada de la misma línea completa.
144. V144: Devolución aprobada requiere usuario aprobador.
145. V145: Rechazo de devolución requiere motivo.
146. V146: Recepción de devolución requiere bodega si vuelve a stock.
147. V147: Producto dañado requiere clasificación.
148. V148: Nota de crédito requiere devolución aprobada.
149. V149: Monto de devolución no puede superar monto facturado.
150. V150: Devolución cerrada no permite edición.
151. V151: Orden de compra requiere proveedor.
152. V152: Orden de compra requiere fecha.
153. V153: Orden de compra requiere al menos una línea.
154. V154: Línea de compra requiere producto.
155. V155: Línea de compra requiere cantidad mayor a cero.
156. V156: Línea de compra requiere precio mayor o igual a cero.
157. V157: Orden aprobada no permite editar líneas sin permiso.
158. V158: Recepción requiere orden de compra aprobada.
159. V159: Recepción requiere bodega.
160. V160: Cantidad recibida mayor a cero.
161. V161: Cantidad recibida no puede superar pendiente más tolerancia.
162. V162: Factura de compra requiere proveedor.
163. V163: Factura de compra requiere número.
164. V164: Factura de compra requiere fecha.
165. V165: Total factura de compra mayor o igual a cero.
166. V166: Impuesto factura de compra mayor o igual a cero.
167. V167: Factura de compra duplicada bloqueada.
168. V168: Orden anulada no permite recepción.
169. V169: Recepción anulada revierte inventario.
170. V170: Producto no comprable no puede ir en orden de compra.
171. V171: Receta requiere producto terminado.
172. V172: Receta requiere versión.
173. V173: Receta requiere al menos un insumo.
174. V174: Insumo de receta requiere producto.
175. V175: Cantidad de insumo mayor a cero.
176. V176: Producto terminado no puede ser insumo de sí mismo.
177. V177: Solo una receta activa por producto y versión vigente.
178. V178: Orden de producción requiere producto terminado.
179. V179: Orden de producción requiere cantidad mayor a cero.
180. V180: Orden de producción requiere fecha requerida.
181. V181: Orden requiere receta activa.
182. V182: Liberación requiere stock suficiente de insumos.
183. V183: Consumo de insumo mayor o igual a cero.
184. V184: Producción reportada mayor o igual a cero.
185. V185: Merma mayor o igual a cero.
186. V186: Producción buena más merma no debe exceder tolerancia configurada.
187. V187: Orden cerrada no permite consumo.
188. V188: Orden cerrada no permite producción adicional.
189. V189: Orden anulada no permite movimientos.
190. V190: Cierre requiere conciliación de consumos.
191. V191: Factura requiere cliente.
192. V192: Factura requiere al menos una línea.
193. V193: Factura requiere número único.
194. V194: Factura requiere fecha de emisión.
195. V195: Neto más impuestos debe igualar total.
196. V196: Nota de crédito requiere factura original.
197. V197: Nota de crédito no puede superar saldo de factura.
198. V198: Pago requiere factura.
199. V199: Pago requiere monto mayor a cero.
200. V200: Alerta por correo requiere al menos un destinatario válido.

---

# F. Endpoints REST

## Base

`/api/v1`

## 130 endpoints

1. `POST /api/v1/auth/login` — iniciar sesión.
2. `POST /api/v1/auth/refresh` — renovar token.
3. `POST /api/v1/auth/logout` — cerrar sesión.
4. `GET /api/v1/auth/me` — obtener usuario autenticado.
5. `POST /api/v1/auth/change-password` — cambiar contraseña.
6. `GET /api/v1/users` — listar usuarios.
7. `POST /api/v1/users` — crear usuario.
8. `GET /api/v1/users/{id}` — obtener usuario.
9. `PATCH /api/v1/users/{id}` — actualizar usuario.
10. `DELETE /api/v1/users/{id}` — inactivar usuario.
11. `GET /api/v1/roles` — listar roles.
12. `POST /api/v1/roles` — crear rol.
13. `PATCH /api/v1/roles/{id}` — actualizar rol.
14. `GET /api/v1/permissions` — listar permisos.
15. `PUT /api/v1/roles/{id}/permissions` — asignar permisos a rol.
16. `GET /api/v1/customers` — listar clientes.
17. `POST /api/v1/customers` — crear cliente.
18. `GET /api/v1/customers/{id}` — obtener cliente.
19. `PATCH /api/v1/customers/{id}` — actualizar cliente.
20. `DELETE /api/v1/customers/{id}` — inactivar cliente.
21. `GET /api/v1/customers/{id}/contacts` — listar contactos.
22. `POST /api/v1/customers/{id}/contacts` — crear contacto.
23. `PATCH /api/v1/customer-contacts/{id}` — actualizar contacto.
24. `DELETE /api/v1/customer-contacts/{id}` — eliminar contacto.
25. `GET /api/v1/customers/{id}/credit` — consultar crédito.
26. `PATCH /api/v1/customers/{id}/credit` — actualizar crédito.
27. `GET /api/v1/customers/{id}/statement` — estado de cuenta.
28. `GET /api/v1/suppliers` — listar proveedores.
29. `POST /api/v1/suppliers` — crear proveedor.
30. `GET /api/v1/suppliers/{id}` — obtener proveedor.
31. `PATCH /api/v1/suppliers/{id}` — actualizar proveedor.
32. `DELETE /api/v1/suppliers/{id}` — inactivar proveedor.
33. `GET /api/v1/suppliers/{id}/contacts` — listar contactos de proveedor.
34. `POST /api/v1/suppliers/{id}/contacts` — crear contacto proveedor.
35. `GET /api/v1/products` — listar productos.
36. `POST /api/v1/products` — crear producto.
37. `GET /api/v1/products/{id}` — obtener producto.
38. `PATCH /api/v1/products/{id}` — actualizar producto.
39. `DELETE /api/v1/products/{id}` — inactivar producto.
40. `GET /api/v1/product-categories` — listar categorías.
41. `POST /api/v1/product-categories` — crear categoría.
42. `GET /api/v1/units` — listar unidades.
43. `POST /api/v1/units` — crear unidad.
44. `GET /api/v1/warehouses` — listar bodegas.
45. `POST /api/v1/warehouses` — crear bodega.
46. `PATCH /api/v1/warehouses/{id}` — actualizar bodega.
47. `GET /api/v1/warehouses/{id}/locations` — listar ubicaciones.
48. `POST /api/v1/warehouses/{id}/locations` — crear ubicación.
49. `GET /api/v1/inventory/stocks` — consultar stock.
50. `GET /api/v1/inventory/movements` — consultar movimientos.
51. `POST /api/v1/inventory/adjustments` — crear ajuste.
52. `POST /api/v1/inventory/transfers` — transferir stock.
53. `POST /api/v1/inventory/counts` — iniciar conteo físico.
54. `GET /api/v1/inventory/counts/{id}` — obtener conteo.
55. `PUT /api/v1/inventory/counts/{id}/lines` — cargar líneas de conteo.
56. `POST /api/v1/inventory/counts/{id}/approve` — aprobar conteo.
57. `POST /api/v1/inventory/counts/{id}/close` — cerrar conteo.
58. `GET /api/v1/sales-orders` — listar ventas.
59. `POST /api/v1/sales-orders` — crear venta.
60. `GET /api/v1/sales-orders/{id}` — obtener venta.
61. `PATCH /api/v1/sales-orders/{id}` — actualizar venta.
62. `POST /api/v1/sales-orders/{id}/confirm` — confirmar venta.
63. `POST /api/v1/sales-orders/{id}/cancel` — anular venta.
64. `POST /api/v1/sales-orders/{id}/reserve-stock` — reservar stock.
65. `POST /api/v1/sales-orders/{id}/release-stock` — liberar reserva.
66. `GET /api/v1/quotations` — listar cotizaciones.
67. `POST /api/v1/quotations` — crear cotización.
68. `POST /api/v1/quotations/{id}/convert-to-sales-order` — convertir cotización a venta.
69. `POST /api/v1/sales-dispatches` — crear despacho.
70. `GET /api/v1/sales-dispatches/{id}` — obtener despacho.
71. `POST /api/v1/sales-dispatches/{id}/cancel` — anular despacho.
72. `GET /api/v1/sales-returns` — listar devoluciones.
73. `POST /api/v1/sales-returns` — crear devolución.
74. `GET /api/v1/sales-returns/{id}` — obtener devolución.
75. `POST /api/v1/sales-returns/{id}/approve` — aprobar devolución.
76. `POST /api/v1/sales-returns/{id}/reject` — rechazar devolución.
77. `POST /api/v1/sales-returns/{id}/receive` — recibir productos devueltos.
78. `POST /api/v1/sales-returns/{id}/create-credit-note` — crear nota de crédito.
79. `GET /api/v1/purchase-orders` — listar órdenes de compra.
80. `POST /api/v1/purchase-orders` — crear orden de compra.
81. `GET /api/v1/purchase-orders/{id}` — obtener orden de compra.
82. `PATCH /api/v1/purchase-orders/{id}` — actualizar orden de compra.
83. `POST /api/v1/purchase-orders/{id}/approve` — aprobar orden de compra.
84. `POST /api/v1/purchase-orders/{id}/cancel` — anular orden de compra.
85. `POST /api/v1/goods-receipts` — registrar recepción.
86. `GET /api/v1/goods-receipts/{id}` — obtener recepción.
87. `POST /api/v1/goods-receipts/{id}/cancel` — anular recepción.
88. `GET /api/v1/supplier-invoices` — listar facturas de compra.
89. `POST /api/v1/supplier-invoices` — registrar factura de compra.
90. `GET /api/v1/supplier-invoices/{id}` — obtener factura de compra.
91. `GET /api/v1/production/boms` — listar recetas.
92. `POST /api/v1/production/boms` — crear receta.
93. `GET /api/v1/production/boms/{id}` — obtener receta.
94. `PATCH /api/v1/production/boms/{id}` — actualizar receta.
95. `POST /api/v1/production/boms/{id}/activate` — activar receta.
96. `GET /api/v1/production/orders` — listar órdenes de producción.
97. `POST /api/v1/production/orders` — crear orden de producción.
98. `GET /api/v1/production/orders/{id}` — obtener orden de producción.
99. `POST /api/v1/production/orders/{id}/release-materials` — liberar insumos.
100. `POST /api/v1/production/orders/{id}/report-output` — reportar producción.
101. `POST /api/v1/production/orders/{id}/close` — cerrar orden.
102. `POST /api/v1/production/orders/{id}/cancel` — anular orden.
103. `GET /api/v1/invoices` — listar facturas.
104. `POST /api/v1/invoices` — emitir factura.
105. `GET /api/v1/invoices/{id}` — obtener factura.
106. `POST /api/v1/invoices/{id}/cancel` — anular factura.
107. `POST /api/v1/invoices/{id}/send-email` — enviar factura por correo.
108. `POST /api/v1/credit-notes` — emitir nota de crédito.
109. `POST /api/v1/debit-notes` — emitir nota de débito.
110. `GET /api/v1/payments` — listar pagos.
111. `POST /api/v1/payments` — registrar pago.
112. `POST /api/v1/payments/{id}/cancel` — anular pago.
113. `GET /api/v1/dashboard/summary` — resumen general.
114. `GET /api/v1/dashboard/sales` — indicadores de ventas.
115. `GET /api/v1/dashboard/inventory` — indicadores de inventario.
116. `GET /api/v1/dashboard/production` — indicadores de producción.
117. `GET /api/v1/reports/sales` — reporte de ventas.
118. `GET /api/v1/reports/inventory` — reporte de inventario.
119. `GET /api/v1/reports/purchases` — reporte de compras.
120. `GET /api/v1/reports/production` — reporte de producción.
121. `GET /api/v1/reports/billing` — reporte de facturación.
122. `POST /api/v1/reports/export` — exportar reporte.
123. `GET /api/v1/alerts` — listar alertas.
124. `POST /api/v1/alerts` — crear alerta.
125. `GET /api/v1/alerts/{id}` — obtener alerta.
126. `PATCH /api/v1/alerts/{id}` — actualizar alerta.
127. `POST /api/v1/alerts/{id}/activate` — activar alerta.
128. `POST /api/v1/alerts/{id}/pause` — pausar alerta.
129. `GET /api/v1/email-logs` — consultar correos enviados.
130. `POST /api/v1/email-logs/{id}/retry` — reintentar correo fallido.

---

# G. Estados recomendados por módulo

## Clientes

`active`, `inactive`, `blocked`

## Productos

`active`, `inactive`

## Ventas

`draft`, `confirmed`, `partially_dispatched`, `dispatched`, `invoiced`, `cancelled`

## Cotizaciones

`draft`, `issued`, `expired`, `converted`, `cancelled`

## Devoluciones

`requested`, `approved`, `rejected`, `received`, `credited`, `closed`

## Compras

`draft`, `issued`, `approved`, `partially_received`, `received`, `cancelled`

## Producción

`planned`, `released`, `in_process`, `partially_completed`, `completed`, `closed`, `cancelled`

## Facturas

`draft`, `issued`, `partially_paid`, `paid`, `cancelled`, `credited`

## Alertas

`active`, `paused`, `inactive`

---

# H. Modelo básico de permisos

1. `customers.read`
2. `customers.create`
3. `customers.update`
4. `customers.delete`
5. `customers.credit.manage`
6. `products.read`
7. `products.create`
8. `products.update`
9. `products.delete`
10. `inventory.read`
11. `inventory.adjust`
12. `inventory.transfer`
13. `inventory.count`
14. `sales.read`
15. `sales.create`
16. `sales.update`
17. `sales.confirm`
18. `sales.cancel`
19. `sales.discount.authorize`
20. `returns.read`
21. `returns.create`
22. `returns.approve`
23. `returns.receive`
24. `purchases.read`
25. `purchases.create`
26. `purchases.approve`
27. `purchases.receive`
28. `production.read`
29. `production.create`
30. `production.release`
31. `production.close`
32. `billing.read`
33. `billing.issue`
34. `billing.cancel`
35. `payments.create`
36. `reports.read`
37. `reports.export`
38. `alerts.manage`
39. `users.manage`
40. `audit.read`

---

# I. Endpoint recomendado como patrón principal

El mejor patrón para este ERP es:

```http
POST /api/v1/{resource}/{id}/{action}
```

Solo para acciones de negocio que cambian estado.

Ejemplos buenos:

```http
POST /api/v1/sales-orders/{id}/confirm
POST /api/v1/purchase-orders/{id}/approve
POST /api/v1/production/orders/{id}/release-materials
POST /api/v1/invoices/{id}/send-email
POST /api/v1/sales-returns/{id}/approve
```

Para CRUD normal:

```http
GET    /api/v1/products
POST   /api/v1/products
GET    /api/v1/products/{id}
PATCH  /api/v1/products/{id}
DELETE /api/v1/products/{id}
```

Este diseño queda simple, consistente y escalable para web, móvil o integraciones.

---

# J. Desarrollo SDD para PROYECTO_CUATRO

## J.1 Metadatos de control

| campo | valor |
|---|---|
| proyecto | `PROYECTO_CUATRO` |
| producto | ERP web pequeño |
| version_spec | `sdd-2026-06-08` |
| workflow | `sdd-extended-1.0` |
| arnes | obligatorio |
| orquestador | obligatorio |
| entrada valida | `harness.run_agent(agent_id, state)` |
| estado objetivo | especificacion lista para planificacion e implementacion |
| costo externo permitido | `0.000000 USD` en modo local deterministico |
| no_inventar | `true` |

## J.2 Alcance cerrado para MVP

Incluye:

1. Autenticacion, usuarios, roles, permisos y auditoria.
2. Clientes, contactos y credito comercial.
3. Productos, categorias, unidades, bodegas, ubicaciones, stock, movimientos, ajustes, transferencias y conteo fisico.
4. Cotizaciones, ordenes de venta, despacho, pagos y anulaciones.
5. Devoluciones, recepcion de devolucion y notas de credito.
6. Proveedores, ordenes de compra, recepcion y facturas de compra.
7. Recetas, ordenes de produccion, consumo de insumos, reporte de produccion, merma y cierre.
8. Facturacion de venta, notas de credito, notas de debito y pagos.
9. Dashboard, reportes exportables y alertas por correo en modo configurable.
10. API REST `/api/v1` con eliminacion logica, auditoria y acciones de estado.

Excluye del MVP:

1. Integracion tributaria real con servicios externos.
2. Envio real de correos sin contrato SMTP/API aprobado.
3. Contabilidad completa, conciliacion bancaria y nomina.
4. POS fiscal certificado.
5. Multiempresa con consolidacion contable avanzada.
6. Deploy productivo, lectura de secretos o acceso a datos reales sin aprobacion.

## J.3 Supuestos funcionales

1. La empresa opera con una moneda base y una zona horaria configurable.
2. Cada registro operativo pertenece a `company_id`.
3. La eliminacion fisica no se usa para entidades con historial operativo.
4. Stock disponible se calcula como `stock_fisico - stock_reservado`.
5. Produccion consume insumos al liberar o registrar consumo, segun configuracion.
6. Facturacion externa queda desacoplada por adaptador futuro.
7. Reportes de alto volumen pueden ejecutarse de forma diferida.
8. Alertas por correo registran intento, resultado, destinatarios e idempotencia.

## J.4 Arquitectura objetivo

Capas:

1. Frontend web: aplicacion responsive con rutas protegidas, formularios con validacion local, tablas paginadas y estados de carga, vacio y error.
2. API REST: `/api/v1`, validacion de entrada, permisos por accion, transacciones por caso de uso y respuestas JSON consistentes.
3. Dominio: servicios por modulo con reglas de negocio puras y eventos de auditoria.
4. Persistencia: base relacional con constraints, indices y soft delete.
5. Jobs: alertas, reportes diferidos, reintento de correos y vencimientos.
6. Observabilidad: logs estructurados, auditoria funcional, metricas de latencia, errores y consumo.

Stack recomendado sin imponer dependencia cerrada:

| capa | recomendacion |
|---|---|
| frontend | React/Next.js o equivalente SPA SSR-ready |
| backend | Node.js/NestJS, Python/FastAPI o equivalente con OpenAPI |
| base datos | PostgreSQL |
| cache/colas | Redis para jobs, idempotencia y cache de reportes |
| archivos | storage compatible S3 para exportaciones |
| auth | JWT/OIDC con refresh token revocable |
| documentacion API | OpenAPI 3.1 |

## J.5 Modelo de dominio canonico

Entidades base:

| entidad | proposito | campos clave |
|---|---|---|
| `companies` | separacion de datos por empresa | `id`, `name`, `tax_id`, `timezone`, `currency`, `status` |
| `users` | identidad operativa | `id`, `company_id`, `email`, `password_hash`, `status` |
| `roles` | agrupacion de permisos | `id`, `company_id`, `name`, `status` |
| `role_permissions` | permisos por rol | `role_id`, `permission_code` |
| `audit_logs` | historial de acciones | `actor_id`, `entity`, `entity_id`, `action`, `before`, `after`, `ip`, `created_at` |

Clientes y ventas:

| entidad | proposito | campos clave |
|---|---|---|
| `customers` | cliente comercial | `company_id`, `tax_id`, `legal_name`, `email`, `payment_term_days`, `credit_limit`, `credit_status` |
| `customer_contacts` | contactos por cliente | `customer_id`, `name`, `email`, `phone`, `is_primary` |
| `quotations` | cotizacion previa | `customer_id`, `expires_at`, `status`, `subtotal`, `tax_total`, `total` |
| `sales_orders` | orden de venta | `customer_id`, `status`, `stock_policy`, `subtotal`, `tax_total`, `total` |
| `sales_order_lines` | lineas de venta | `sales_order_id`, `product_id`, `quantity`, `unit_price`, `discount`, `tax_rate` |
| `sales_dispatches` | despacho | `sales_order_id`, `warehouse_id`, `status`, `dispatched_at` |
| `sales_returns` | devoluciones | `sales_order_id`, `customer_id`, `reason`, `status` |

Inventario y compras:

| entidad | proposito | campos clave |
|---|---|---|
| `products` | maestro de productos | `sku`, `name`, `unit_id`, `track_stock`, `sale_price`, `cost`, `status` |
| `product_categories` | clasificacion | `company_id`, `name`, `status` |
| `units` | unidades de medida | `company_id`, `name`, `symbol`, `status` |
| `warehouses` | bodegas | `company_id`, `code`, `name`, `status` |
| `warehouse_locations` | ubicaciones internas | `warehouse_id`, `code`, `name`, `status` |
| `inventory_stocks` | saldo actual | `product_id`, `warehouse_id`, `location_id`, `physical_qty`, `reserved_qty` |
| `inventory_movements` | kardex | `product_id`, `warehouse_id`, `type`, `quantity`, `reason`, `source_type`, `source_id` |
| `suppliers` | proveedores | `company_id`, `tax_id`, `legal_name`, `payment_term_days`, `status` |
| `purchase_orders` | compras | `supplier_id`, `status`, `subtotal`, `tax_total`, `total` |
| `goods_receipts` | recepcion | `purchase_order_id`, `warehouse_id`, `status`, `received_at` |
| `supplier_invoices` | factura de compra | `supplier_id`, `number`, `issued_at`, `total`, `status` |

Produccion y facturacion:

| entidad | proposito | campos clave |
|---|---|---|
| `production_boms` | receta versionada | `product_id`, `version`, `status`, `standard_waste_pct` |
| `production_bom_lines` | insumos de receta | `bom_id`, `component_product_id`, `quantity`, `unit_id` |
| `production_orders` | orden de produccion | `product_id`, `bom_id`, `planned_qty`, `produced_qty`, `waste_qty`, `status` |
| `production_consumptions` | consumo real | `production_order_id`, `product_id`, `required_qty`, `consumed_qty` |
| `invoices` | factura de venta | `customer_id`, `sales_order_id`, `number`, `status`, `total`, `balance` |
| `credit_notes` | nota de credito | `invoice_id`, `reason`, `total`, `status` |
| `debit_notes` | nota de debito | `invoice_id`, `concept`, `total`, `status` |
| `payments` | pagos | `invoice_id`, `amount`, `method`, `reference`, `status` |

Alertas y reportes:

| entidad | proposito | campos clave |
|---|---|---|
| `dashboard_preferences` | widgets por usuario | `user_id`, `widgets`, `filters` |
| `alerts` | regla de alerta | `type`, `condition`, `frequency`, `recipients`, `status` |
| `email_logs` | intentos de correo | `alert_id`, `recipient`, `status`, `attempts`, `last_error` |
| `report_exports` | exportaciones | `user_id`, `report_type`, `filters_hash`, `file_url`, `status` |

## J.6 Reglas transaccionales criticas

1. Confirmar venta debe validar cliente activo, credito, precios, descuentos, impuestos y stock.
2. Reserva de stock debe ser atomica por producto y bodega.
3. Despacho debe crear movimientos de salida y actualizar la orden en la misma transaccion.
4. Recepcion de compra debe crear entrada de inventario y dejar trazabilidad al documento origen.
5. Ajuste de inventario debe requerir motivo y aprobacion si supera umbral.
6. Liberacion de produccion debe bloquear si no hay insumos suficientes, salvo politica de faltantes aprobada.
7. Cierre de produccion debe conciliar insumos, producto terminado, merma y costo real.
8. Nota de credito no puede superar saldo facturado disponible.
9. Pago no puede superar saldo salvo anticipo autorizado.
10. Toda accion de estado debe ser idempotente o rechazar repeticion con estado actual claro.

## J.7 Contrato de API

Formato comun de respuesta exitosa:

```json
{
  "data": {},
  "meta": {
    "request_id": "REQ-TBD",
    "timestamp": "2026-06-08T00:00:00Z"
  }
}
```

Formato comun de error:

```json
{
  "error": {
    "code": "validation_error",
    "message": "La solicitud contiene campos invalidos.",
    "details": [
      {
        "field": "customer_id",
        "issue": "required"
      }
    ]
  },
  "meta": {
    "request_id": "REQ-TBD"
  }
}
```

Codigos minimos:

| codigo | uso |
|---|---|
| `validation_error` | input invalido |
| `permission_denied` | permiso insuficiente |
| `not_found` | recurso inexistente o inaccesible |
| `state_conflict` | accion no permitida por estado |
| `stock_unavailable` | stock insuficiente |
| `credit_blocked` | cliente bloqueado o excedido |
| `duplicate_record` | unicidad violada |
| `external_service_unavailable` | integracion externa falla |

## J.8 Requisitos no funcionales

| id | requisito | criterio |
|---|---|---|
| RNF-01 | Seguridad | contraseñas con hash fuerte, JWT expirable, refresh revocable, RBAC por permiso |
| RNF-02 | Auditoria | 100% de cambios criticos con actor, fecha, antes/despues e IP |
| RNF-03 | Rendimiento | listados paginados; p95 API menor a 800 ms en consultas comunes con indices |
| RNF-04 | Integridad | transacciones en ventas, compras, inventario, produccion y facturacion |
| RNF-05 | Disponibilidad | jobs reintentables y acciones idempotentes en procesos asincronos |
| RNF-06 | Exportacion | reportes exportables con registro de usuario, filtros y archivo generado |
| RNF-07 | Accesibilidad | pantallas administrativas con contraste AA, foco visible y navegacion por teclado |
| RNF-08 | Observabilidad | logs estructurados con `request_id`, `user_id`, `company_id`, modulo y latencia |
| RNF-09 | Privacidad | costos, deuda y reportes financieros ocultos por permiso |
| RNF-10 | Mantenibilidad | OpenAPI, migraciones versionadas y pruebas por caso critico |

## J.9 Criterios de aceptacion por modulo

| modulo | aceptacion minima |
|---|---|
| Clientes | crear, editar, consultar, gestionar credito e inactivar con auditoria y duplicados bloqueados |
| Inventario | kardex trazable, stock por bodega, ajustes aprobables, conteo fisico y transferencias atomicas |
| Ventas | cotizacion, conversion, venta directa, confirmacion, reserva, despacho y anulacion por estado |
| Devoluciones | solicitud, aprobacion, recepcion, nota de credito y rechazo con cantidades controladas |
| Compras | proveedor, orden, aprobacion, recepcion, factura y cuenta por pagar basica |
| Produccion | BOM versionada, orden, liberacion, consumo, reporte, merma, cierre y costo real |
| Facturacion | factura, nota de credito, nota de debito, pagos, saldo y anulacion controlada |
| Reportes | dashboard y reportes filtrables con permisos y exportacion auditada |
| Alertas | configuracion, ejecucion, idempotencia, logs y reintentos |
| Seguridad | RBAC, sesiones, permisos de costo/deuda y auditoria completa |

## J.10 Estrategia de pruebas

Pruebas unitarias:

1. Validaciones V001 a V200.
2. Calculos monetarios, impuestos, descuentos y totales.
3. Calculo de stock disponible, reservado y comprometido.
4. Transiciones de estado por modulo.
5. Reglas de credito, stock, aprobaciones y anulaciones.

Pruebas de integracion:

1. Venta confirmada con reserva y despacho.
2. Venta facturada con pago parcial, total y nota de credito.
3. Compra aprobada con recepcion y entrada de inventario.
4. Produccion con consumo, merma y cierre.
5. Devolucion con recepcion y nota de credito.
6. Alertas de stock bajo, facturas vencidas y correos fallidos.

Pruebas E2E:

1. Login, crear cliente, crear producto, crear venta y facturar.
2. Conteo fisico con aprobacion y ajuste.
3. Orden de produccion completa hasta cierre.
4. Reporte exportado con auditoria.

## J.11 Trazabilidad macro

| requisito | fuente | prueba requerida | evidencia |
|---|---|---|---|
| REQ-CLI | UC-CLI-01..05 | unit + E2E cliente | clientes, contactos, credito, auditoria |
| REQ-INV | UC-INV-01..06 | unit + integracion inventario | kardex, stocks, ajustes, conteos |
| REQ-VTA | UC-VTA-01..05 | integracion venta | orden, reserva, despacho, anulacion |
| REQ-DEV | UC-DEV-01..05 | integracion devolucion | solicitud, recepcion, nota credito |
| REQ-COM | UC-COM-01..05 | integracion compra | orden, aprobacion, recepcion |
| REQ-PROD | UC-PROD-01..05 | integracion produccion | BOM, consumo, reporte, cierre |
| REQ-FAC | UC-FAC-01..05 | integracion facturacion | factura, nota, pago, saldo |
| REQ-REP | UC-REP-01..05 | E2E reportes | filtros, exportacion, permisos |
| REQ-ALT | UC-ALT-01..05 | integracion jobs | alerta, email_logs, reintentos |
| REQ-SEC | P-39, P-40, permisos | security + RBAC | usuarios, roles, auditoria |

## J.12 Ciclo de fabrica aplicado

| paso | aplicacion en PROYECTO_CUATRO |
|---:|---|
| 1 | Work order `WO-PROYECTO-CUATRO-SDD-20260608`, alcance MVP y gate de cierre definidos |
| 2 | Index/cache sobre contratos de fabrica y especificacion del proyecto |
| 3 | Memoria de proyecto aislada en `project/PROYECTO_CUATRO/.fabrica/memory/project` |
| 4 | Logs por run, ciclo, agente y tool en artefactos de fabrica |
| 5 | Billing ledger con tokens estimados y costo externo cero en modo deterministico |
| 6 | Plan de ejecucion por agentes registrados y gates SDD |
| 7 | Ejecucion solo por `harness.run_agent(agent_id, state)` |
| 8 | ValidatorChain para schema, evidencia, policy, seguridad, cobertura, budget y formato |
| 9 | Reintentos solo ante fallas reparables y dentro de presupuesto |
| 10 | Cache/index invalidable si cambia la especificacion |
| 11 | Reporte de resultado, gates, evidencia y costos |
| 12 | Cierre con `billing-ledger.json`, `final-report.json` y handoff |

## J.13 Registro de consumo y optimizacion

Politica de consumo:

1. Modo de este desarrollo: local deterministico sin llamadas externas.
2. `billing-ledger.json` es la fuente de consumo por fase.
3. `consumption-register.json` del proyecto resume el ledger y conserva el hash.
4. Si se usa API real en el futuro, se debe pasar `api_usage` por fase y modelo con tarifa oficial versionada.
5. Si falta tarifa oficial, el costo queda `not_answerable`; no se inventa precio.

Optimizaciones obligatorias:

1. Reutilizar index/cache antes de reconstruir contexto.
2. Consultar chunks y no documentos completos cuando baste evidencia parcial.
3. Separar memoria factory y memoria project.
4. Bloquear web, secretos, deploy y correo real en especificacion y pruebas.
5. Agrupar validaciones por modulo para reducir ejecuciones repetidas.
6. Mantener OpenAPI como contrato para generar clientes, pruebas y documentacion desde una sola fuente.
7. Ejecutar reportes pesados como jobs diferidos con cache por `filters_hash`.
8. Usar paginacion, filtros indexados y proyecciones de columnas en listados.

## J.14 Riesgos y decisiones

| riesgo | impacto | mitigacion |
|---|---|---|
| Integracion tributaria no definida | bloqueo de facturacion real | adaptador futuro con contrato separado |
| Reglas de impuestos por pais | calculos incorrectos | parametrizar impuestos y validar por jurisdiccion antes de deploy |
| Stock concurrente | sobreventa | transacciones, locks por stock y operaciones idempotentes |
| Reportes grandes | latencia alta | jobs diferidos, cache y exportaciones asincronas |
| Permisos incompletos | fuga de datos financieros | matriz RBAC y pruebas de autorizacion |
| Correo externo | side effects no aprobados | modo dry-run y proveedor configurable |

## J.15 Gate de cierre de especificacion

La especificacion queda lista cuando:

1. Los modulos MVP tienen casos de uso, pantallas, reglas, validaciones, endpoints y permisos.
2. El modelo de dominio cubre entidades criticas.
3. Cada requisito macro tiene prueba requerida y evidencia esperada.
4. El ciclo de 12 pasos queda registrado por arnes/orquestador.
5. El consumo queda registrado y el costo externo no supera el presupuesto aprobado.
6. No hay deploy, secretos, correo real ni integraciones externas ejecutadas sin aprobacion.
