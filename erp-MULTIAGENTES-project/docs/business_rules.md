# Reglas de Negocio - ERP Veterinaria

> **Autor:** @AnalistaNegocio  
> **Normativa:** Ley 19.628 (Privacidad de datos) · Ley de Derechos y Deberes del Paciente (Chile)

---

## Principios Generales

| Principio        | Detalle                                                              |
|------------------|----------------------------------------------------------------------|
| Moneda           | Pesos Chilenos (CLP), sin decimales                                  |
| Formato de fecha | ISO 8601: `AAAA-MM-DD`                                               |
| UX Clínica       | Máximo **3 clics** para cualquier acción crítica                     |
| Confirmaciones   | Siempre mostrar estado visual claro: ✅ Éxito / ❌ Error             |
| Doble registro   | Bloquear duplicados con validación en frontend Y backend             |

---

## Módulos Planificados

- [ ] Gestión de Adultos Mayores (Ficha Clínica)
- [ ] Gestión de Tutores / Contactos de Emergencia
- [ ] Agenda y Citas
- [ ] Facturación (CLP)
- [ ] Reportes y Auditoría

---

## Flujo de Trabajo del Equipo

```
@AnalistaNegocio → @Arquitecto → @Programador → @QA → @Arquitecto (cierre)
```

Cada agente debe esperar el **Paso de Posta** explícito del agente anterior antes de actuar.

---

*Este documento es completado y mantenido por @AnalistaNegocio.*

