# 🤖 Multi-Agentes — Framework de Desarrollo de Software con IA

> **Sistema multiagente que coordina 4 agentes de IA especializados para generar software de forma autónoma**, siguiendo un flujo de trabajo profesional con control de calidad integrado.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![DeepSeek API](https://img.shields.io/badge/LLM-DeepSeek-purple?logo=openai&logoColor=white)](https://deepseek.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 ¿Qué es este proyecto?

**Multi-Agentes** es un orquestador que coordina un equipo de **4 agentes de IA especializados** para generar software de forma colaborativa. Cada agente tiene un rol profesional definido y se comunican mediante un protocolo de **Paso de Posta**, replicando cómo trabaja un equipo de desarrollo real:

```
📋 Analista de Negocio  →  🏗️ Arquitecto  →  💻 Programador  →  🧪 QA
```

El sistema incluye control anti-ciclo, persistencia de sesiones, verificaciones automáticas de calidad, inyección de archivos como contexto y escalamiento automático al usuario cuando la IA no puede resolver un problema.

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     🎮 ORQUESTADOR                          │
│   Coordina flujo, detecta Paso de Posta, anti-ciclo,        │
│   persistencia de sesiones, retry con backoff exponencial    │
├──────────┬──────────┬──────────────┬────────────────────────┤
│          │          │              │                        │
│  📋 BA   │ 🏗️ Arq  │  💻 Prog     │  🧪 QA                │
│  T=0.7   │  T=0.3   │   T=0.2      │   T=0.1               │
│          │          │              │                        │
│ Requeri- │ Diseño   │ Código       │ Testing                │
│ mientos  │ técnico  │ Python/SQL   │ automatizado           │
│ y flujos │ y datos  │ prolijo      │ + 7 verificaciones     │
└──────────┴──────────┴──────────────┴────────────────────────┘
         ↕               ↕               ↕
    business_rules.md  architecture.md  src/**  tests/**
```

---

## 🚀 Quickstart

### 1. Clonar e instalar

```powershell
git clone https://github.com/MiguelLeivaLegua/multi-agentes.git
cd multi-agentes/erp-MULTIAGENTES-project
pip install -r requirements.txt
```

### 2. Configurar credenciales

```powershell
copy .env.example .env
# Editar .env con tu API key de DeepSeek
```

### 3. Iniciar el orquestador

```powershell
python orquestador.py
```

---

## 💬 Comandos del Orquestador

| Comando | Descripción |
|---|---|
| `@Agente mensaje` | Enviar mensaje directo a un agente específico |
| `flujo mensaje` | Ejecutar cadena completa: Analista → Arquitecto → Programador → QA |
| `verificar` | Ejecutar 7 verificaciones automatizadas de QA + análisis del agente |
| `estado` | Ver estado de agentes, historial y tokens estimados |
| `reset @Agente` | Reiniciar contexto de un agente específico |
| `sesiones` | Listar sesiones guardadas disponibles |
| `cargar <id>` | Restaurar sesión anterior (ej: `cargar 20260514_181400`) |
| `exportar` | Exportar sesión completa a Markdown |
| `guardar` | Guardar snapshot completo + log JSON |
| `salir` | Terminar sesión (auto-guarda) |

### Ejemplo de uso

```
🧑 Usuario > @AnalistaNegocio Define el flujo de ingreso de paciente al sistema
🧑 Usuario > flujo Crear módulo de autenticación con validación de RUT
🧑 Usuario > @Programador revisa ./src/services/deepseek_client.py
🧑 Usuario > verificar
```

---

## 🤖 Equipo de Agentes

| Agente | Rol | Temperatura | Responsabilidad |
|---|---|---|---|
| `@AnalistaNegocio` | Business Analyst Senior | 0.7 | Requerimientos funcionales, flujos de usuario, criterios de aceptación |
| `@Arquitecto` | Arquitecto de Software | 0.3 | Diseño técnico, modelo de datos, seguridad OWASP, CHANGELOG |
| `@Programador` | Lead Developer | 0.2 | Implementación en Python/SQL, código prolijo y documentado |
| `@QA` | QA Engineer | 0.1 | Testing automatizado, 7 verificaciones de calidad, veredicto final |

Cada agente tiene su **system prompt especializado** almacenado en `CONFIGURACION/*.modelfile`, diseñado con reglas estrictas de comportamiento, formato de respuesta y criterios de calidad.

---

## 🔄 Flujo de Trabajo — Paso de Posta

El sistema replica un flujo de desarrollo profesional con **puntos de control del usuario**:

```
PASO 1: @AnalistaNegocio   →  Define requerimientos
             ↓
PASO 2: @Usuario            →  APRUEBA requerimientos        ← PUNTO DE CONTROL
             ↓
PASO 3: @Arquitecto         →  Diseña la arquitectura
             ↓
PASO 4: @AnalistaNegocio    →  Valida diseño vs reglas de negocio
             ↓
PASO 5: @Usuario            →  APRUEBA el diseño técnico     ← PUNTO DE CONTROL
             ↓
PASO 6: @Programador        →  Implementa el código
             ↓
PASO 7: @QA                 →  Prueba (manual + verificar)
             ↓
PASO 8: @Arquitecto         →  Registra hito en CHANGELOG
```

**Regla de bloqueo:** ningún agente avanza sin el Paso de Posta del anterior.
**Anti-ciclo:** cada agente tiene máximo **3 intentos** por tarea antes de escalar al usuario.

---

## 🧪 Verificaciones Automáticas de QA

El comando `verificar` ejecuta **7 verificaciones** sobre el código fuente:

| # | Verificación | Qué detecta |
|---|---|---|
| 1 | Estructura | `__init__.py` faltantes, docs, `.env`, `.gitignore`, tests |
| 2 | Rutas absolutas | `C:\Users` y similares hardcodeados en `.py` |
| 3 | Secrets expuestos | API keys, contraseñas en texto plano en código |
| 4 | SQL inseguro | f-strings y concatenación en `cursor.execute()` |
| 5 | Dependencias | Imports sin declarar en `requirements.txt` |
| 6 | Gitignore | `.env` no protegido en `.gitignore` |
| 7 | Pytest | Ejecuta `pytest ./tests/` y captura resultados |

Los resultados se envían automáticamente al agente `@QA` para un veredicto estructurado (APROBADO/RECHAZADO).

---

## ⚙️ Características Técnicas

- **Timeout configurable** en llamadas a DeepSeek (default: 120s)
- **Retry con backoff exponencial** (hasta 3 reintentos: 1s, 2s, 4s)
- **Auto-guardado** cada 5 interacciones + al recibir `Ctrl+C`
- **Escritura atómica** de snapshots (`.tmp` → rename, previene corrupción)
- **Restauración de sesiones** completa desde disco
- **Inyección automática de archivos** cuando el usuario referencia una ruta
- **Idioma español forzado** en todos los prompts para mantener consistencia

---

## 📁 Estructura del Proyecto

```
multi-agentes/
├── README.md                           ← Este archivo
├── .gitignore                          ← Protección de archivos sensibles
│
├── CONFIGURACION/                      ← System prompts de los agentes
│   ├── AnalistaNegocio.modelfile
│   ├── Arquitecto.modelfile
│   ├── Programador.modelfile
│   └── QA.modelfile
│
└── erp-MULTIAGENTES-project/           ← Proyecto ERP generado por los agentes
    ├── orquestador.py                  ← Motor multiagente principal
    ├── main.py                         ← Punto de entrada del ERP
    ├── requirements.txt                ← Dependencias Python
    ├── .env.example                    ← Plantilla de variables de entorno
    ├── CONTEXT.md                      ← Contexto completo para IAs
    ├── docs/
    │   ├── business_rules.md           ← Reglas de negocio (@AnalistaNegocio)
    │   ├── architecture.md             ← Arquitectura técnica (@Arquitecto)
    │   └── CHANGELOG.md                ← Cronología de progreso
    ├── src/
    │   ├── services/
    │   │   ├── deepseek_client.py      ← Cliente API con timeout + historial
    │   │   └── qa_herramientas.py      ← Toolbox automatizado de QA
    │   ├── api/                        ← Endpoints (en desarrollo)
    │   └── db/                         ← Migraciones SQL Server (en desarrollo)
    ├── tests/
    │   └── test_main.py                ← Suite de pruebas
    └── logs/                           ← Snapshots y logs JSON por sesión
```

---

## 🔐 Seguridad

| Principio | Implementación |
|---|---|
| **Secrets protegidos** | `.env` excluido de Git. Nunca en código fuente |
| **Timeout API** | Configurable vía `DEEPSEEK_TIMEOUT` (default: 120s) |
| **SQL parametrizado** | Prohibida la concatenación de strings en queries |
| **Anti-ciclo** | Máx. 3 intentos por agente/tarea → escalamiento automático |
| **Rutas absolutas** | Prohibidas en código. Siempre relativas |
| **Audit log** | Log JSON de eventos por sesión |

---

## 📄 Licencia

MIT — Libre para uso personal y comercial.

---

## 👨‍💻 Autor

**Miguel Leiva Legua**
- GitHub: [@MiguelLeivaLegua](https://github.com/MiguelLeivaLegua)
