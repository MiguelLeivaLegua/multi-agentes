# ERP Veterinaria - Sistema de Gestión Clínica para Centros de Adultos Mayores

> Proyecto multiagente con IA (DeepSeek) para desarrollo asistido del ERP.
> Cada agente tiene un rol especializado y se comunican mediante **Paso de Posta**.

> 🧠 **¿Primera vez aquí o eres una IA?** Lee primero [`CONTEXT.md`](./CONTEXT.md) —
> contiene todo el contexto del proyecto en un solo archivo.

---

## Requisitos

- **Python 3.10+**
- **SQL Server** (para producción)
- **API Key de DeepSeek** (configurada en `.env`)

## Instalación

```powershell
cd erp-veterinaria-project
pip install -r requirements.txt
```

## Configuración

Copiar `.env.example` a `.env` y completar las variables:

```
DEEPSEEK_API_KEY=tu-api-key-aquí
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=120
DB_HOST=localhost
DB_NAME=erp_veterinaria
DB_USER=tu-usuario
DB_PASSWORD=tu-contraseña
```

### Variable `DEEPSEEK_TIMEOUT`

Controla el timeout (en segundos) de cada llamada a la API de DeepSeek.
Si DeepSeek no responde dentro de ese tiempo, la llamada falla con excepción
en vez de quedarse colgada infinitamente. Por defecto: **120 segundos**.

## Uso del Orquestador

```powershell
python orquestador.py
```

### Comandos disponibles

| Comando | Acción |
|---|---|
| `@Agente mensaje` | Enviar mensaje directo a un agente |
| `flujo mensaje` | Ejecutar cadena completa: Analista → Arquitecto → Programador → QA |
| `verificar` | Ejecutar 7 verificaciones automatizadas de QA + análisis del agente |
| `estado` | Ver estado de agentes, historial y tokens estimados |
| `reset @Agente` | Reiniciar contexto de un agente específico |
| `sesiones` | Listar sesiones guardadas disponibles para restaurar |
| `cargar <id>` | Restaurar sesión anterior (ej: `cargar 20260514_181400`) |
| `exportar` | Exportar sesión completa a Markdown en `/docs/` |
| `guardar` | Guardar snapshot completo + log JSON de la sesión |
| `ayuda` | Mostrar comandos |
| `salir` | Terminar sesión (auto-guarda) |

### Ejemplo de uso

```
🧑 Usuario > @AnalistaNegocio Define el flujo de ingreso de paciente al centro
🧑 Usuario > flujo Crear módulo de ficha clínica con validación de RUT
🧑 Usuario > @Programador revisa ./src/services/deepseek_client.py
🧑 Usuario > verificar
```

---

## Características Técnicas Clave

### 1. Timeout en llamadas API

El cliente DeepSeek (`src/services/deepseek_client.py`) incluye un **timeout configurable**
vía la variable de entorno `DEEPSEEK_TIMEOUT` (por defecto 120s). Si la API no responde,
la llamada falla con error en lugar de bloquear el orquestador indefinidamente.
Además, el orquestador implementa **retry con backoff exponencial** (hasta 3 reintentos
con esperas de 1s, 2s, 4s).

### 2. Auto-guardado con Ctrl+C y guardado periódico

Al presionar `Ctrl+C` o cerrar la consola, el orquestador **intercepta la señal**
(`SIGINT` / `SIGTERM`) y guarda automáticamente:
- Snapshot completo del estado en `/logs/snapshot_<ID>.json`
- El log JSON de eventos en `/logs/sesion_<ID>.json`
- La sesión exportada en Markdown en `/docs/sesion_<ID>.md`

Además, cada **5 interacciones** se auto-guarda un snapshot silenciosamente
(escritura atómica: `.tmp` → rename, para evitar corrupción si el proceso muere).

Nunca se pierde el trabajo de una sesión, incluso en cierre inesperado.

### 2b. Persistencia y restauración de sesiones

Cada sesión se guarda como un **snapshot completo** en `/logs/snapshot_<ID>.json`
que incluye: historiales de los 4 agentes, contadores de intentos, tokens estimados
y log de eventos. Esto permite restaurar una sesión exactamente donde se dejó:

```
🧑 Usuario > sesiones           ← Lista todas las sesiones guardadas
🧑 Usuario > cargar 20260514_181400  ← Restaura esa sesión
```

Al restaurar, se recupera el historial completo de cada agente, pudiendo
continuar la conversación como si nunca se hubiera cerrado.

### 3. Inyección de archivos como contexto

Cuando el usuario menciona una ruta de archivo en su mensaje
(por ejemplo `revisa ./src/services/deepseek_client.py`), el orquestador:
1. Detecta automáticamente rutas con patrón `./src/...`, `src/...`, `tests/...`, `docs/...`
2. Lee el contenido del archivo (hasta 3000 caracteres)
3. Lo inyecta como mensaje de sistema para que el agente lo vea en contexto

Ejemplo:
```
🧑 Usuario > @Programador revisa ./src/services/deepseek_client.py
```
El agente recibe el contenido real del archivo y puede analizarlo.

### 4. Idioma español forzado en prompts

Todos los system prompts incluyen automáticamente la instrucción:
```
IDIOMA OBLIGATORIO: Responde SIEMPRE en español (Chile).
Nunca cambies al inglés, ni siquiera para términos técnicos comunes.
```
Esto previene que DeepSeek responda en inglés.

### 5. Paquetes Python (`__init__.py`)

Todos los subdirectorios de `src/` son paquetes Python importables:
- `src/__init__.py`
- `src/api/__init__.py`
- `src/db/__init__.py`
- `src/services/__init__.py`

### 6. Herramientas automatizadas de QA

El comando `verificar` ejecuta **7 verificaciones automáticas** sobre el código
y envía el informe al agente `@QA` para que emita su veredicto:

| # | Verificación | Qué detecta |
|---|---|---|
| 1 | Estructura | `__init__.py` faltantes, docs, `.env`, `.gitignore`, tests |
| 2 | Rutas absolutas | `C:\Users` y similares en archivos `.py` |
| 3 | Secrets expuestos | API keys, contraseñas en texto plano en código |
| 4 | SQL inseguro | f-strings y concatenación en `cursor.execute()` |
| 5 | Dependencias | Imports sin declarar en `requirements.txt` |
| 6 | Gitignore | `.env` no protegido en `.gitignore` |
| 7 | Pytest | Ejecuta `pytest ./tests/` y captura resultados |

El `@QA` interpreta el informe y emite un veredicto estructurado
(APROBADO/RECHAZADO) con la tabla de casos de prueba.

También se puede ejecutar directamente:
```powershell
python src/services/qa_herramientas.py
```

---

## Equipo de Agentes

| Agente | Rol | Archivos que mantiene |
|---|---|---|
| `@AnalistaNegocio` | BA Senior — requerimientos y UX clínica | `business_rules.md` |
| `@Arquitecto` | Arquitecto — diseño, seguridad, OWASP | `architecture.md`, `CHANGELOG.md` |
| `@Programador` | Lead Dev — implementación Python/Go + SQL | `./src/**`, `requirements.txt` |
| `@QA` | QA Engineer — testing y validación de ley | `./tests/**` |

## Flujo de trabajo (Paso de Posta con validaciones)

```
1. @AnalistaNegocio  →  define requerimientos
         ↓
2. @Usuario          →  aprueba requerimientos        ← PUNTO DE CONTROL
         ↓
3. @Arquitecto       →  diseña la arquitectura
         ↓
4. @AnalistaNegocio  →  valida que el diseño respeta las reglas de negocio
         ↓
5. @Usuario          →  aprueba el diseño técnico     ← PUNTO DE CONTROL
         ↓
6. @Programador      →  implementa
         ↓
7. @QA               →  prueba (manual + verificar automático)
         ↓
8. @Arquitecto       →  registra hito en CHANGELOG.md (cierre)
```

**Regla de bloqueo:** ningún agente puede avanzar sin el Paso de Posta del anterior.
El `@Programador` **no puede** iniciar sin diseño aprobado por `@Usuario`.

### Anti-ciclo

Cada agente tiene un máximo de **3 intentos** por tarea. Si los agota, escala
automáticamente al `@Usuario` para intervención manual.

---

## Estándares de código prolijo

Reglas obligatorias que el `@Programador` aplica y el `@QA` verifica:

| Regla | Detalle |
|---|---|
| **Funciones cortas** | Máx. 30 líneas — si es más larga, dividirla en subfunciones |
| **Docstrings** | Toda función/clase con docstring en español (qué hace, params, retorno) |
| **Sin código muerto** | Sin imports sin usar, funciones sin llamar, comentarios obsoletos |
| **Nombres descriptivos** | `validar_rut_chileno()` no `vr()`. `fecha_nacimiento` no `fn` |
| **Un archivo = una responsabilidad** | Si supera 200 líneas → dividir en módulos |
| **Constantes en MAYÚSCULAS** | Al inicio del archivo, nunca dentro de funciones |
| **Manejo de errores** | Todo bloque crítico con `try-except` y registro del error |
| **SQL parametrizado** | Nunca concatenar strings en consultas — siempre parámetros |

## Estructura del proyecto

```
erp-veterinaria-project/
├── docs/
│   ├── business_rules.md    ← @AnalistaNegocio
│   ├── architecture.md      ← @Arquitecto
│   └── CHANGELOG.md         ← Cronología (fuente de verdad)
├── src/
│   ├── __init__.py          ← Paquete Python
│   ├── api/                 ← Endpoints
│   │   └── __init__.py
│   ├── db/                  ← Migraciones SQL Server
│   │   └── __init__.py
│   └── services/            ← Lógica de negocio
│       ├── __init__.py
│       ├── deepseek_client.py ← Cliente de API con timeout
│       └── qa_herramientas.py ← Toolbox automatizado del @QA (7 verificaciones)
├── tests/
│   └── test_main.py         ← Suite de QA
├── logs/                    ← Logs JSON por sesión (auto-guardados)
├── orquestador.py           ← Motor multiagente (Paso de Posta + anti-ciclo)
├── main.py                  ← Punto de entrada del ERP
├── requirements.txt         ← Dependencias Python
├── .env                     ← Variables de entorno (NO subir a Git)
└── .gitignore               ← Protege .env y archivos sensibles
```

## Normativa

- **Ley 19.628** — Protección de datos personales (Chile)
- **Ley de Derechos y Deberes del Paciente** — Regulación de datos clínicos
- RUT y diagnósticos siempre encriptados (AES-256)
- Audit logging obligatorio

