# 🧠 CONTEXT.md — Contexto Completo del Proyecto ERP Veterinaria
> **Para IAs:** Lee este archivo primero. Contiene todo lo que necesitas saber para
> contribuir al proyecto sin preguntar ni adivinar. Versión actualizada: 2026-05-14.

---

## 1. ¿Qué es este proyecto?

**ERP Veterinaria** es un sistema de gestión clínica para **centros de adultos mayores** en Chile.
Desarrollado como un **sistema multiagente con IA** donde 4 agentes especializados
(AnalistaNegocio, Arquitecto, Programador, QA) colaboran bajo coordinación de un orquestador.

- **Stack:** Python 3.10+, SQL Server, DeepSeek API (compatible con OpenAI SDK)
- **Entorno:** Windows Local (PowerShell)
- **Normativa:** Ley 19.628 (Privacidad de datos) + Ley de Derechos y Deberes del Paciente (Chile)
- **Idioma del código:** Español (variables, funciones, comentarios, docstrings — todo en español)

---

## 2. Estructura de directorios

```
erp-veterinaria-project/                ← raíz del proyecto Python
├── orquestador.py                ← Motor principal del sistema multiagente
├── main.py                       ← Punto de entrada del ERP
├── requirements.txt              ← Dependencias Python
├── .env                          ← Variables de entorno (NO subir a Git)
├── .gitignore                    ← Protege .env y archivos sensibles
│
├── src/
│   ├── __init__.py
│   ├── api/                      ← Puntos de acceso (endpoints) HTTP/REST
│   │   └── __init__.py
│   ├── db/                       ← Migraciones y conexión SQL Server
│   │   └── __init__.py
│   └── services/                 ← Lógica de negocio
│       ├── __init__.py
│       ├── deepseek_client.py    ← Cliente DeepSeek (timeout + historial)
│       └── qa_herramientas.py    ← Toolbox automatizado del @QA
│
├── tests/
│   └── test_main.py              ← Suite de pruebas pytest
│
├── docs/
│   ├── business_rules.md         ← Reglas de negocio (@AnalistaNegocio)
│   ├── architecture.md           ← Arquitectura del sistema (@Arquitecto)
│   └── CHANGELOG.md              ← Fuente de verdad del progreso (@Arquitecto)
│
└── logs/                         ← Snapshots y logs JSON de cada sesión (auto-generado)
    ├── snapshot_<ID>.json        ← Estado completo restaurable por sesión
    └── sesion_<ID>.json          ← Log de eventos de la sesión

CONFIGURACION/                    ← System prompts de los agentes (fuera del proyecto Python)
├── AnalistaNegocio.modelfile     ← Prompt V6 del @AnalistaNegocio
├── Arquitecto.modelfile          ← Prompt V6 del @Arquitecto
├── Programador.modelfile         ← Prompt V6 del @Programador
└── QA.modelfile                  ← Prompt V6 del @QA
```

---

## 3. Variables de entorno (.env)

```env
DEEPSEEK_API_KEY=sk-...           # Clave de acceso a DeepSeek (OBLIGATORIO)
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=120              # Segundos antes de timeout (default: 120)
DB_HOST=localhost
DB_NAME=eleam_erp
DB_USER=tu-usuario
DB_PASSWORD=tu-contraseña
```

**Regla de oro:** nunca escribir estos valores directamente en código. Siempre `os.getenv("...")`.

---

## 4. Los 4 Agentes y sus responsabilidades

| Agente | Versión | Rol | Archivos que mantiene |
|---|---|---|---|
| `@AnalistaNegocio` | V6 | Define requerimientos funcionales, flujos de usuario, criterios de aceptación | `docs/business_rules.md` |
| `@Arquitecto` | V6 | Diseña arquitectura (Mermaid), modelo de datos SQL, puntos de acceso | `docs/architecture.md`, `docs/CHANGELOG.md` |
| `@Programador` | V6 | Implementa en Python/Go + SQL. Código prolijo, rutas relativas, SQL parametrizado | `src/**`, `requirements.txt` |
| `@QA` | V6 | Pruebas funcionales + seguridad + portabilidad + código prolijo | `tests/**` |

**Temperatura de cada agente:**
- `@AnalistaNegocio`: 0.7 (creativo para requerimientos)
- `@Arquitecto`: 0.3 (preciso para diseño técnico)
- `@Programador`: 0.2 (determinista para código)
- `@QA`: 0.1 (muy determinista para pruebas)

---

## 5. Flujo de trabajo obligatorio (con puntos de control)

```
PASO 1: @AnalistaNegocio  →  define requerimientos
              ↓
PASO 2: @Usuario           →  APRUEBA requerimientos        ← PUNTO DE CONTROL
              ↓
PASO 3: @Arquitecto        →  diseña arquitectura
              ↓
PASO 4: @AnalistaNegocio   →  valida que el diseño respeta las reglas de negocio
              ↓
PASO 5: @Usuario           →  APRUEBA el diseño técnico     ← PUNTO DE CONTROL
              ↓
PASO 6: @Programador       →  implementa el código
              ↓
PASO 7: @QA                →  prueba (manual + verificar automático)
              ↓
PASO 8: @Arquitecto        →  registra hito en CHANGELOG.md (cierre)
```

**Regla crítica:** ningún agente actúa sin el Paso de Posta explícito del anterior.
`@Programador` está bloqueado hasta que `@Usuario` apruebe el diseño (Paso 5).

---

## 6. Comandos del orquestador

```powershell
python orquestador.py   # Iniciar
```

| Comando | Acción |
|---|---|
| `@Agente mensaje` | Enviar mensaje directo a un agente |
| `flujo mensaje` | Ejecutar cadena completa AnalistaNegocio → QA |
| `verificar` | 7 verificaciones automáticas de QA + análisis del agente |
| `estado` | Ver estado de todos los agentes, historial y tokens |
| `sesiones` | Listar snapshots guardados |
| `cargar <id>` | Restaurar sesión anterior (ej: `cargar 20260514_181400`) |
| `exportar` | Exportar sesión a Markdown en `/docs/` |
| `guardar` | Guardar snapshot + log JSON ahora |
| `salir` | Terminar (auto-guarda antes de cerrar) |

---

## 7. Herramientas automatizadas de QA (`verificar`)

El comando `verificar` ejecuta `src/services/qa_herramientas.py` y envía el informe al `@QA`:

| # | Verificación | Qué detecta | Estado si falla |
|---|---|---|---|
| 1 | Estructura | `__init__.py`, docs, `.env`, `.gitignore`, tests | RECHAZADO |
| 2 | Rutas absolutas | `C:\Users` y similares en `.py` | RECHAZADO |
| 3 | Secrets expuestos | API keys, contraseñas en texto plano | RECHAZADO |
| 4 | SQL inseguro | f-strings en `cursor.execute()` | RECHAZADO |
| 5 | Dependencias | Imports no declarados en `requirements.txt` | RECHAZADO |
| 6 | Gitignore | `.env` no protegido | RECHAZADO |
| 7 | Pytest | Ejecuta `pytest ./tests/` | RECHAZADO si tests fallan |

También ejecutable directamente: `python src/services/qa_herramientas.py`

---

## 8. Estándares de código (obligatorios para el @Programador)

| Regla | Detalle |
|---|---|
| **Idioma** | Todo en español: variables, funciones, comentarios, docstrings |
| **Funciones cortas** | Máx. 30 líneas. Si es más larga → dividirla |
| **Docstrings** | Toda función/clase tiene docstring en español |
| **Sin código muerto** | Sin imports sin usar, sin funciones sin llamar |
| **Nombres descriptivos** | `validar_rut_chileno()` no `vr()`. `fecha_nacimiento` no `fn` |
| **Rutas relativas** | Siempre `./src/...`. Nunca `C:\Users\...` |
| **Un archivo = una responsabilidad** | Si supera 200 líneas → dividir en módulos |
| **Constantes en MAYÚSCULAS** | Al inicio del archivo, nunca dentro de funciones |
| **SQL parametrizado** | Nunca concatenar strings en consultas |
| **Try-except** | Todo bloque crítico con manejo de excepciones y registro del error |

---

## 9. Persistencia de sesiones

El orquestador guarda snapshots en `/logs/snapshot_<ID>.json` con:
- Historiales completos de los 4 agentes
- Contadores de intentos por tarea (anti-ciclo)
- Tokens estimados por agente
- Log de eventos de la sesión

**Auto-guardado:** cada 5 interacciones + al recibir `SIGINT`/`SIGTERM` (Ctrl+C).
**Escritura atómica:** escribe en `.tmp` y luego hace rename para evitar corrupción.

---

## 10. Seguridad y normativa

| Principio | Implementación |
|---|---|
| **Ley 19.628** | RUT y diagnósticos encriptados (AES-256) en BD. Nunca en texto plano. |
| **Timeout API** | `DEEPSEEK_TIMEOUT=120` — nunca se queda colgado infinitamente |
| **Retry con backoff** | 3 reintentos con esperas 1s, 2s, 4s ante fallo de API |
| **Anti-ciclo** | Máx. 3 intentos por agente/tarea → escalamiento automático al @Usuario |
| **Inyección SQL** | Consultas 100% parametrizadas |
| **Secrets** | Nunca en código. Solo en `.env` (excluido de Git) |
| **Rutas absolutas** | Prohibidas en código fuente |
| **Audit log** | Log de eventos JSON por sesión en `/logs/` |

---

## 11. Modelo de datos base (SQL Server)

```sql
-- Tablas principales (español, sin rutas absolutas, AES-256 para datos sensibles)
PACIENTES (id_paciente PK, nombre, rut_encriptado, fecha_nacimiento, estado)
CONTACTOS_TUTOR (id_tutor PK, id_paciente FK, nombre_tutor, telefono, relacion)
REGISTRO_AUDITORIA (id PK, usuario, accion, tabla_afectada, fecha_hora)

-- Índices para búsquedas < 200ms
CREATE INDEX IX_Pacientes_RUT ON Pacientes(rut_encriptado);
CREATE INDEX IX_Pacientes_Nombre ON Pacientes(nombre);
```

---

## 12. Anti-patrones que este proyecto RECHAZA

- ❌ Rutas absolutas (`C:\Users\Miguel\...`)
- ❌ API keys en código fuente
- ❌ SQL con concatenación de strings (`"SELECT * FROM " + tabla`)
- ❌ Variables de nombre críptico (`fn`, `vr`, `tmp2`)
- ❌ Funciones de más de 30 líneas sin dividir
- ❌ Código en inglés (variables, comentarios, docstrings)
- ❌ Pasar al siguiente agente sin Paso de Posta explícito
- ❌ Implementar sin diseño aprobado por `@Usuario`
- ❌ Aprobar QA sin ejecutar `verificar`

---

## 13. Cómo retomar el proyecto

```powershell
# 1. Instalar dependencias
cd erp-veterinaria-project
pip install -r requirements.txt

# 2. Configurar .env (copiar .env.example si existe)
# Completar DEEPSEEK_API_KEY y datos de BD

# 3. Iniciar
python orquestador.py

# 4. Si hay sesión previa
sesiones           # Lista sesiones guardadas
cargar 20260514_xxxxxx  # Restaurar la última sesión

# 5. Verificar estado del código
verificar          # Corre las 7 verificaciones de QA
```

---

## 14. Contexto de sesiones activas

> **Nota para IAs:** El archivo `/docs/CHANGELOG.md` es la fuente de verdad del progreso.
> El archivo `/docs/business_rules.md` contiene los requerimientos aprobados.
> El archivo `/docs/architecture.md` contiene el diseño técnico vigente.
> Antes de proponer cambios, lee estos 3 archivos.

---

*Mantenido manualmente. Actualizar cuando cambien: flujo de agentes, comandos del
orquestador, estructura de directorios, o estándares de código.*

