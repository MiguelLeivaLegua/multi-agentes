"""
orquestador.py - Orquestador del Equipo Multiagente ERP Veterinaria
Autor: @Programador (Lead Developer)

Propósito:
    Coordina a los 4 agentes (AnalistaNegocio, Arquitecto, Programador, QA)
    gestionando contexto independiente, historial de conversación, inyección
    de documentos, detección de Paso de Posta, anti-ciclo y escalamiento.

Uso:
    python orquestador.py
"""

import os
import re
import sys
import json
import time
import signal
import atexit
from datetime import datetime
from pathlib import Path

# ─── Fix encoding para consola de Windows (cp1252 no soporta emojis) ────────
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# Importamos el cliente DeepSeek como paquete (src/services/ tiene __init__.py)
from src.services.deepseek_client import consultar_con_historial
from src.services.qa_herramientas import generar_informe_completo as informe_qa


# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE RUTAS (relativas a la raíz del proyecto)
# ═══════════════════════════════════════════════════════════════

RAIZ_PROYECTO = Path(__file__).parent
RUTA_CONFIGURACION = RAIZ_PROYECTO.parent / "CONFIGURACION"
RUTA_DOCS = RAIZ_PROYECTO / "docs"
RUTA_LOGS = RAIZ_PROYECTO / "logs"

# Crear directorio de logs si no existe
RUTA_LOGS.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# DEFINICIÓN DE AGENTES
# ═══════════════════════════════════════════════════════════════

AGENTES = {
    "AnalistaNegocio": {
        "archivo_prompt": RUTA_CONFIGURACION / "AnalistaNegocio.modelfile",
        "docs_relevantes": ["business_rules.md", "CHANGELOG.md"],
        "temperatura": 0.7,
        "siguiente": "Arquitecto",  # Flujo normal de Paso de Posta
    },
    "Arquitecto": {
        "archivo_prompt": RUTA_CONFIGURACION / "Arquitecto.modelfile",
        "docs_relevantes": ["architecture.md", "business_rules.md", "CHANGELOG.md"],
        "temperatura": 0.5,
        "siguiente": "Programador",
    },
    "Programador": {
        "archivo_prompt": RUTA_CONFIGURACION / "Programador.modelfile",
        "docs_relevantes": ["architecture.md", "CHANGELOG.md"],
        "temperatura": 0.4,
        "siguiente": "QA",
    },
    "QA": {
        "archivo_prompt": RUTA_CONFIGURACION / "QA.modelfile",
        "docs_relevantes": ["business_rules.md", "architecture.md", "CHANGELOG.md"],
        "temperatura": 0.3,
        "siguiente": "Arquitecto",  # QA cierra el ciclo con el Arquitecto
    },
}

# Patrones para detectar Paso de Posta en las respuestas
PATRON_PASO_POSTA = re.compile(
    r"@(AnalistaNegocio|Arquitecto|Programador|QA|Usuario)",
    re.IGNORECASE,
)

# Patrones para detectar estado de la respuesta
PATRON_ESTADO = re.compile(
    r"##\s*ESTADO:\s*\[?(COMPLETO|EN_PROGRESO|BLOQUEADO|ESCALADO|APROBADO|RECHAZADO)\]?",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════
# CLASE PRINCIPAL: CONTEXTO POR AGENTE
# ═══════════════════════════════════════════════════════════════

class ContextoAgente:
    """
    Maneja el contexto individual de cada agente:
    - System prompt cargado desde .modelfile
    - Historial de conversación (mensajes)
    - Documentos inyectados como contexto
    - Contador de intentos por tarea (anti-ciclo)
    - Estimación de tokens consumidos
    """

    def __init__(self, nombre: str, config: dict):
        self.nombre = nombre
        self.config = config
        self.system_prompt = self._cargar_prompt()
        self.historial: list[dict] = []  # Mensajes de la conversación
        self.intentos: dict[str, int] = {}  # {tarea: contador}
        self.max_intentos = 3
        self.tokens_estimados = 0  # Aproximación de tokens consumidos

    def _cargar_prompt(self) -> str:
        """Carga el system prompt desde el archivo .modelfile."""
        ruta = self.config["archivo_prompt"]
        if not ruta.exists():
            raise FileNotFoundError(f"[ERROR] No se encontró el archivo de prompt: {ruta}")

        contenido = ruta.read_text(encoding="utf-8")

        # Extraer solo el contenido entre SYSTEM """ ... """
        match = re.search(r'SYSTEM\s+"""(.*?)"""', contenido, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Si no tiene el formato SYSTEM """, usar todo el contenido
        return contenido.strip()

    def _cargar_documentos_contexto(self) -> str:
        """
        Lee los documentos relevantes del agente y los compacta
        para inyectar como contexto adicional.
        """
        contexto_docs = []
        for nombre_doc in self.config["docs_relevantes"]:
            ruta_doc = RUTA_DOCS / nombre_doc
            if ruta_doc.exists():
                contenido = ruta_doc.read_text(encoding="utf-8")
                # Limitar a 2000 chars por doc para no saturar el contexto
                if len(contenido) > 2000:
                    contenido = contenido[:2000] + "\n[... DOCUMENTO TRUNCADO — ver archivo completo ...]"
                contexto_docs.append(f"=== DOCUMENTO: {nombre_doc} ===\n{contenido}")

        if contexto_docs:
            return "\n\n".join(contexto_docs)
        return ""

    def construir_mensajes(self, mensaje_usuario: str) -> list[dict]:
        """
        Construye la lista completa de mensajes para enviar a la API:
        1. System prompt del agente + instrucción de idioma
        2. Documentos de contexto inyectados
        3. Archivos referenciados en el mensaje (detección automática)
        4. Historial de conversación previo
        5. Nuevo mensaje del usuario
        """
        mensajes = []

        # 1. System prompt + forzar idioma español
        prompt_con_idioma = (
            self.system_prompt
            + "\n\nIDIOMA OBLIGATORIO: Responde SIEMPRE en español (Chile). "
            "Nunca cambies al inglés, ni siquiera para términos técnicos comunes."
        )
        mensajes.append({"role": "system", "content": prompt_con_idioma})

        # 2. Documentos de contexto del proyecto
        docs = self._cargar_documentos_contexto()
        if docs:
            mensajes.append({
                "role": "system",
                "content": (
                    "DOCUMENTOS DE REFERENCIA DEL PROYECTO (consulta antes de preguntar):\n\n"
                    + docs
                ),
            })

        # 3. Archivos referenciados en el mensaje (detección automática)
        archivos_inyectados = self._detectar_e_inyectar_archivos(mensaje_usuario)
        if archivos_inyectados:
            mensajes.append({
                "role": "system",
                "content": "ARCHIVOS REFERENCIADOS POR EL USUARIO:\n\n" + archivos_inyectados,
            })

        # 4. Historial previo de esta conversación
        mensajes.extend(self.historial)

        # 5. Nuevo mensaje del usuario
        mensajes.append({"role": "user", "content": mensaje_usuario})

        return mensajes

    def _detectar_e_inyectar_archivos(self, mensaje: str) -> str:
        """
        Detecta rutas relativas (./src/...) en el mensaje del usuario
        y lee su contenido para inyectarlo como contexto.
        Ejemplo: 'revisa ./src/services/auth.py' -> inyecta el archivo.
        """
        # Buscar patrones de ruta: ./algo, src/algo, tests/algo
        patron_ruta = re.findall(r'(?:\./)?(?:src|tests|docs)/[\w/._-]+\.\w+', mensaje)
        if not patron_ruta:
            return ""

        contenidos = []
        for ruta_relativa in patron_ruta:
            ruta = RAIZ_PROYECTO / ruta_relativa.lstrip('./')
            if ruta.exists() and ruta.is_file():
                try:
                    texto = ruta.read_text(encoding='utf-8')
                    if len(texto) > 3000:
                        texto = texto[:3000] + "\n[... ARCHIVO TRUNCADO ...]\n"
                    contenidos.append(f"=== ARCHIVO: {ruta_relativa} ===\n```\n{texto}\n```")
                except Exception:
                    contenidos.append(f"=== ARCHIVO: {ruta_relativa} === [ERROR AL LEER]")

        return "\n\n".join(contenidos)

    def agregar_al_historial(self, rol: str, contenido: str):
        """Agrega un mensaje al historial de este agente."""
        self.historial.append({"role": rol, "content": contenido})
        # Estimación: ~4 chars = 1 token (aproximación para español)
        self.tokens_estimados += len(contenido) // 4

    def registrar_intento(self, tarea: str) -> int:
        """Registra un intento para una tarea. Retorna el número de intento actual."""
        if tarea not in self.intentos:
            self.intentos[tarea] = 0
        self.intentos[tarea] += 1
        return self.intentos[tarea]

    def intentos_agotados(self, tarea: str) -> bool:
        """¿Se agotaron los 3 intentos para esta tarea?"""
        return self.intentos.get(tarea, 0) >= self.max_intentos

    def limpiar_historial(self):
        """Limpia el historial manteniendo solo un resumen."""
        if len(self.historial) > 20:
            resumen = f"[RESUMEN] Historial compactado. Se mantienen los últimos 10 mensajes de {len(self.historial)} totales."
            self.historial = [{"role": "system", "content": resumen}] + self.historial[-10:]

    def resetear(self):
        """Reinicia completamente el contexto del agente."""
        self.historial = []
        self.intentos = {}
        self.tokens_estimados = 0

    def total_mensajes(self) -> int:
        """Retorna el total de mensajes en el historial."""
        return len(self.historial)

    def exportar_historial_md(self) -> str:
        """Exporta el historial del agente como Markdown legible."""
        lineas = [f"# Historial de @{self.nombre}\n"]
        lineas.append(f"Tokens estimados: ~{self.tokens_estimados}\n")
        for msg in self.historial:
            rol = "Usuario" if msg["role"] == "user" else f"@{self.nombre}"
            lineas.append(f"### {rol}\n")
            lineas.append(msg["content"])
            lineas.append("\n---\n")
        return "\n".join(lineas)


# ═══════════════════════════════════════════════════════════════
# CLASE PRINCIPAL: ORQUESTADOR
# ═══════════════════════════════════════════════════════════════

class Orquestador:
    """
    Coordina la comunicación entre agentes del equipo multiagente.
    
    Responsabilidades:
    - Mantiene contexto separado por agente.
    - Detecta Paso de Posta y rutea al agente siguiente.
    - Aplica anti-ciclo (máx. 3 intentos por tarea).
    - Escala al Usuario cuando es necesario.
    - Guarda logs de toda la sesión.
    - Persiste y restaura sesiones completas desde disco.
    """

    # Cada cuántas interacciones se auto-guarda un snapshot (best practice: no perder trabajo)
    AUTO_GUARDAR_CADA = 5

    def __init__(self):
        self.agentes: dict[str, ContextoAgente] = {}
        self.agente_activo: str = None
        self.sesion_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_sesion: list[dict] = []
        self._interacciones_desde_guardado = 0  # Contador para auto-guardado periódico

        # Inicializar contexto de cada agente
        for nombre, config in AGENTES.items():
            self.agentes[nombre] = ContextoAgente(nombre, config)

        print("=" * 60)
        print("  🏥 ERP Veterinaria - Orquestador Multiagente")
        print("  📋 Agentes: AnalistaNegocio → Arquitecto → Programador → QA")
        print(f"  🆔 Sesión: {self.sesion_id}")
        print("=" * 60)

    # ─── Enviar mensaje a un agente ─────────────────────────────

    def enviar_a_agente(self, nombre_agente: str, mensaje: str, tarea: str = "general") -> str:
        """
        Envía un mensaje a un agente específico, gestionando contexto e historial.
        
        Parámetros:
            nombre_agente : Nombre del agente destino.
            mensaje       : Texto a enviar.
            tarea         : Identificador de la tarea (para anti-ciclo).
            
        Retorna:
            str: Respuesta del agente.
        """
        if nombre_agente not in self.agentes:
            return f"[ERROR] Agente '{nombre_agente}' no existe. Disponibles: {list(self.agentes.keys())}"

        agente = self.agentes[nombre_agente]
        self.agente_activo = nombre_agente

        # Anti-ciclo: verificar intentos
        intento = agente.registrar_intento(tarea)
        if agente.intentos_agotados(tarea):
            msg_escalar = (
                f"\n⚠️ ESCALAMIENTO AUTOMÁTICO ⚠️\n"
                f"El agente @{nombre_agente} ha agotado {agente.max_intentos} intentos en la tarea '{tarea}'.\n"
                f"Se requiere intervención del @Usuario para continuar.\n"
            )
            self._log("ESCALAMIENTO", nombre_agente, msg_escalar)
            return msg_escalar

        # Gestión de contexto: compactar si hay muchos mensajes
        agente.limpiar_historial()

        # Construir mensajes con contexto completo
        mensajes = agente.construir_mensajes(mensaje)

        # Informar al usuario
        print(f"\n{'─' * 50}")
        print(f"📨 Enviando a @{nombre_agente} (intento {intento}/{agente.max_intentos} | tarea: {tarea})")
        print(f"📚 Contexto: {len(mensajes)} mensajes ({agente.total_mensajes()} en historial)")
        print(f"{'─' * 50}")

        # Llamar a la API con retry y backoff exponencial (máx. 3 reintentos)
        respuesta = None
        max_reintentos = 3
        for reintento in range(max_reintentos):
            try:
                respuesta = consultar_con_historial(
                    mensajes=mensajes,
                    temperatura=agente.config["temperatura"],
                )
                break  # Éxito, salir del loop de retry
            except Exception as e:
                espera = 2 ** reintento  # 1s, 2s, 4s
                if reintento < max_reintentos - 1:
                    print(f"  ⚠️ Error de API (intento {reintento + 1}/{max_reintentos}). Reintentando en {espera}s...")
                    time.sleep(espera)
                else:
                    error_msg = f"[ERROR] Fallo al comunicarse con @{nombre_agente} tras {max_reintentos} reintentos: {e}"
                    self._log("ERROR", nombre_agente, error_msg)
                    return error_msg

        # Guardar en historial del agente
        agente.agregar_al_historial("user", mensaje)
        agente.agregar_al_historial("assistant", respuesta)

        # Log
        self._log("RESPUESTA", nombre_agente, respuesta)

        # Detectar Paso de Posta
        paso_posta = self._detectar_paso_posta(respuesta)
        estado = self._detectar_estado(respuesta)

        if paso_posta:
            print(f"🔀 Paso de Posta detectado → @{paso_posta}")
        if estado:
            print(f"📊 Estado: {estado}")

        return respuesta

    # ─── Flujo automático: Paso de Posta ────────────────────────

    def ejecutar_flujo(self, agente_inicio: str, mensaje_inicial: str, tarea: str = "general"):
        """
        Ejecuta el flujo completo de agentes siguiendo el Paso de Posta.
        Se detiene cuando:
        - Un agente escala al @Usuario
        - Se completa el ciclo
        - Se agotan los intentos
        
        Parámetros:
            agente_inicio  : Agente que recibe el primer mensaje.
            mensaje_inicial: Requerimiento o tarea a procesar.
            tarea          : Nombre de la tarea (para tracking de intentos).
        """
        agente_actual = agente_inicio
        mensaje_actual = mensaje_inicial
        agentes_visitados = []
        max_saltos = 8  # Máximo de saltos entre agentes para evitar ciclo infinito global

        print(f"\n🚀 Iniciando flujo desde @{agente_actual}")
        print(f"📝 Tarea: {tarea}")

        for salto in range(max_saltos):
            agentes_visitados.append(agente_actual)

            # Enviar al agente
            respuesta = self.enviar_a_agente(agente_actual, mensaje_actual, tarea)
            print(f"\n💬 @{agente_actual} responde:")
            print(respuesta)

            # Detectar siguiente agente
            siguiente = self._detectar_paso_posta(respuesta)
            estado = self._detectar_estado(respuesta)

            # Condiciones de parada
            if siguiente == "Usuario":
                print(f"\n🛑 FLUJO DETENIDO — Se requiere intervención del @Usuario")
                print(f"📋 Ruta seguida: {' → '.join(agentes_visitados)}")
                return respuesta

            if estado and estado.upper() in ("ESCALADO", "BLOQUEADO"):
                print(f"\n🛑 FLUJO DETENIDO — Estado: {estado}")
                print(f"📋 Ruta seguida: {' → '.join(agentes_visitados)}")
                return respuesta

            if estado and estado.upper() in ("COMPLETO", "APROBADO"):
                if siguiente and siguiente in self.agentes:
                    # Continuar al siguiente agente
                    agente_actual = siguiente
                    mensaje_actual = f"[PASO DE POSTA desde @{agentes_visitados[-1]}]\n\n{respuesta}"
                else:
                    print(f"\n✅ FLUJO COMPLETADO — Estado: {estado}")
                    print(f"📋 Ruta seguida: {' → '.join(agentes_visitados)}")
                    return respuesta

            elif siguiente and siguiente in self.agentes:
                agente_actual = siguiente
                mensaje_actual = f"[PASO DE POSTA desde @{agentes_visitados[-1]}]\n\n{respuesta}"
            else:
                # Sin Paso de Posta detectado — esperar input del usuario
                print(f"\n⏸️ FLUJO EN PAUSA — @{agente_actual} no hizo Paso de Posta")
                print(f"📋 Ruta seguida: {' → '.join(agentes_visitados)}")
                return respuesta

        print(f"\n🛑 FLUJO DETENIDO — Máximo de {max_saltos} saltos alcanzado (prevención de ciclo infinito)")
        print(f"📋 Ruta seguida: {' → '.join(agentes_visitados)}")
        return respuesta

    # ─── Detección de patrones ──────────────────────────────────

    def _detectar_paso_posta(self, respuesta: str) -> str | None:
        """Detecta si la respuesta contiene un Paso de Posta (@Agente)."""
        matches = PATRON_PASO_POSTA.findall(respuesta)
        if matches:
            return matches[-1]  # Retornamos la última mención (la del Paso de Posta)
        return None

    def _detectar_estado(self, respuesta: str) -> str | None:
        """Detecta el estado en la respuesta (COMPLETO, BLOQUEADO, etc.)."""
        match = PATRON_ESTADO.search(respuesta)
        if match:
            return match.group(1).upper()
        return None

    # ─── Logging ────────────────────────────────────────────────

    def _log(self, tipo: str, agente: str, contenido: str):
        """Registra un evento en el log de la sesión."""
        entrada = {
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "agente": agente,
            "contenido": contenido[:500],  # Limitar para no inflar el log
        }
        self.log_sesion.append(entrada)

        # Auto-guardado periódico (best practice: no perder trabajo)
        self._interacciones_desde_guardado += 1
        if self._interacciones_desde_guardado >= self.AUTO_GUARDAR_CADA:
            self._guardar_snapshot_silencioso()
            self._interacciones_desde_guardado = 0

    def guardar_log(self):
        """Guarda el log completo de la sesión en un archivo JSON."""
        archivo_log = RUTA_LOGS / f"sesion_{self.sesion_id}.json"
        with open(archivo_log, "w", encoding="utf-8") as f:
            json.dump(self.log_sesion, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Log guardado en: {archivo_log}")

    # ─── Persistencia de sesiones (snapshot completo) ──────────

    def _guardar_snapshot_silencioso(self):
        """Guarda snapshot sin imprimir mensajes (para auto-guardado periódico)."""
        try:
            self._guardar_snapshot(silencioso=True)
        except Exception:
            pass  # No interrumpir el flujo por un fallo de auto-guardado

    def _guardar_snapshot(self, silencioso: bool = False):
        """
        Guarda un snapshot completo de la sesión en disco.
        Incluye: historial de cada agente, intentos, tokens, log de eventos y metadatos.
        Esto permite restaurar la sesión exactamente donde se dejó.
        """
        snapshot = {
            "sesion_id": self.sesion_id,
            "timestamp_guardado": datetime.now().isoformat(),
            "agente_activo": self.agente_activo,
            "agentes": {},
            "log_sesion": self.log_sesion,
        }

        for nombre, agente in self.agentes.items():
            snapshot["agentes"][nombre] = {
                "historial": agente.historial,
                "intentos": agente.intentos,
                "tokens_estimados": agente.tokens_estimados,
            }

        archivo = RUTA_LOGS / f"snapshot_{self.sesion_id}.json"
        # Escritura atómica: escribir a .tmp y luego renombrar (previene corrupción)
        archivo_tmp = archivo.with_suffix(".json.tmp")
        with open(archivo_tmp, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        archivo_tmp.replace(archivo)  # Rename atómico

        if not silencioso:
            print(f"\n💾 Snapshot guardado en: {archivo}")

    def restaurar_sesion(self, sesion_id: str) -> bool:
        """
        Restaura una sesión anterior desde su snapshot en disco.
        Carga los historiales de todos los agentes, intentos, tokens y log.
        
        Parámetros:
            sesion_id: ID de la sesión a restaurar (ej: '20260514_181400').
            
        Retorna:
            bool: True si la restauración fue exitosa.
        """
        archivo = RUTA_LOGS / f"snapshot_{sesion_id}.json"
        if not archivo.exists():
            print(f"  ⚠️ No se encontró snapshot para sesión '{sesion_id}'.")
            self._listar_snapshots_disponibles()
            return False

        try:
            with open(archivo, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ❌ Error al leer snapshot: {e}")
            return False

        # Restaurar estado de cada agente
        for nombre, datos in snapshot.get("agentes", {}).items():
            if nombre in self.agentes:
                agente = self.agentes[nombre]
                agente.historial = datos.get("historial", [])
                agente.intentos = datos.get("intentos", {})
                agente.tokens_estimados = datos.get("tokens_estimados", 0)

        self.agente_activo = snapshot.get("agente_activo")
        self.log_sesion = snapshot.get("log_sesion", [])
        self.sesion_id = sesion_id  # Continuar con el mismo ID

        # Mostrar resumen de lo restaurado
        total_msgs = sum(a.total_mensajes() for a in self.agentes.values())
        total_tokens = sum(a.tokens_estimados for a in self.agentes.values())
        guardado_en = snapshot.get("timestamp_guardado", "desconocido")

        print(f"\n  ✅ Sesión '{sesion_id}' restaurada exitosamente.")
        print(f"  📅 Último guardado: {guardado_en}")
        print(f"  💬 {total_msgs} mensajes en historial | ~{total_tokens} tokens")
        print(f"  👤 Último agente activo: @{self.agente_activo or 'ninguno'}")
        for nombre, agente in self.agentes.items():
            if agente.total_mensajes() > 0:
                print(f"     @{nombre}: {agente.total_mensajes()} msgs, ~{agente.tokens_estimados} tokens")

        return True

    def listar_sesiones(self):
        """Lista todas las sesiones guardadas en disco con su información."""
        self._listar_snapshots_disponibles()

    def _listar_snapshots_disponibles(self):
        """Busca snapshots disponibles en /logs/ y muestra info resumida."""
        snapshots = sorted(RUTA_LOGS.glob("snapshot_*.json"), reverse=True)
        if not snapshots:
            print("  📭 No hay sesiones guardadas en /logs/.")
            return

        print(f"\n{'═' * 60}")
        print("  📋 SESIONES DISPONIBLES PARA RESTAURAR")
        print(f"{'═' * 60}")

        for archivo in snapshots[:10]:  # Mostrar las 10 más recientes
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    snap = json.load(f)
                sid = snap.get("sesion_id", "?")
                guardado = snap.get("timestamp_guardado", "?")
                n_msgs = sum(
                    len(datos.get("historial", []))
                    for datos in snap.get("agentes", {}).values()
                )
                n_eventos = len(snap.get("log_sesion", []))
                activo = snap.get("agente_activo", "ninguno")

                # Marcar si es la sesión actual
                marca = " ← ACTUAL" if sid == self.sesion_id else ""
                print(f"  🆔 {sid}{marca}")
                print(f"     Guardado: {guardado}")
                print(f"     Mensajes: {n_msgs} | Eventos: {n_eventos} | Último agente: @{activo}")
            except Exception:
                print(f"  ⚠️ {archivo.name} (error al leer)")

        print(f"{'═' * 60}")
        print("  💡 Usa: cargar <sesion_id> para restaurar.")

    # ─── Info del estado ────────────────────────────────────────

    def estado_agentes(self):
        """Muestra el estado de cada agente."""
        total_tokens = 0
        print(f"\n{'═' * 60}")
        print("  📊 ESTADO DE LOS AGENTES")
        print(f"{'═' * 60}")
        for nombre, agente in self.agentes.items():
            marca = " 👈 ACTIVO" if nombre == self.agente_activo else ""
            print(f"  @{nombre}{marca}")
            print(f"    Historial: {agente.total_mensajes()} mensajes")
            print(f"    Tokens estimados: ~{agente.tokens_estimados}")
            print(f"    Intentos: {agente.intentos}")
            total_tokens += agente.tokens_estimados
        print(f"{'─' * 60}")
        print(f"  TOTAL TOKENS SESIÓN: ~{total_tokens}")
        print(f"{'═' * 60}")

    def resetear_agente(self, nombre_agente: str):
        """Reinicia el contexto de un agente específico."""
        if nombre_agente in self.agentes:
            self.agentes[nombre_agente].resetear()
            print(f"  🔄 @{nombre_agente} reseteado (historial, intentos y tokens a cero).")
        else:
            print(f"  ⚠️ Agente '{nombre_agente}' no existe.")

    def exportar_sesion_md(self):
        """Exporta toda la sesión como un archivo Markdown en /docs."""
        archivo = RUTA_DOCS / f"sesion_{self.sesion_id}.md"
        lineas = ["# Sesión del Orquestador ERP Veterinaria\n"]
        lineas.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        lineas.append(f"ID: {self.sesion_id}\n\n---\n")
        for nombre, agente in self.agentes.items():
            if agente.total_mensajes() > 0:
                lineas.append(agente.exportar_historial_md())
                lineas.append("\n")
        contenido = "\n".join(lineas)
        archivo.write_text(contenido, encoding="utf-8")
        print(f"  📄 Sesión exportada a: {archivo}")


# ═══════════════════════════════════════════════════════════════
# INTERFAZ INTERACTIVA
# ═══════════════════════════════════════════════════════════════

def main():
    """Interfaz de línea de comandos para el orquestador."""
    orq = Orquestador()

    # Registrar auto-guardado para Ctrl+C y cierre inesperado
    def _auto_guardar(sig=None, frame=None):
        print("\n\n⚠️ Cierre detectado. Auto-guardando sesión...")
        orq.guardar_log()
        orq._guardar_snapshot(silencioso=False)
        orq.exportar_sesion_md()
        print("👋 Sesión guardada. Hasta luego.")
        sys.exit(0)

    signal.signal(signal.SIGINT, _auto_guardar)
    signal.signal(signal.SIGTERM, _auto_guardar)
    atexit.register(orq.guardar_log)
    atexit.register(lambda: orq._guardar_snapshot(silencioso=True))

    print("\n📖 COMANDOS DISPONIBLES:")
    print("  @Agente mensaje    -> Enviar mensaje a un agente especifico")
    print("  flujo mensaje      -> Flujo completo: Analista -> Arquitecto -> Programador -> QA")
    print("  verificar          -> Ejecutar verificaciones automatizadas de QA")
    print("  estado             -> Ver estado de todos los agentes + tokens")
    print("  reset @Agente      -> Reiniciar contexto de un agente")
    print("  sesiones           -> Listar sesiones guardadas")
    print("  cargar <id>        -> Restaurar sesion anterior (ej: cargar 20260514_181400)")
    print("  exportar           -> Exportar sesion completa a Markdown")
    print("  guardar            -> Guardar snapshot + log JSON de la sesion")
    print("  ayuda              -> Mostrar estos comandos")
    print("  salir              -> Terminar sesion (auto-guarda)\n")

    while True:
        try:
            entrada = input("\n🧑 Usuario > ").strip()
        except (EOFError, KeyboardInterrupt):
            _auto_guardar()
            break

        if not entrada:
            continue

        # Comandos especiales
        if entrada.lower() == "salir":
            orq.guardar_log()
            orq._guardar_snapshot(silencioso=False)
            print("👋 Sesión terminada.")
            break

        elif entrada.lower() == "estado":
            orq.estado_agentes()

        elif entrada.lower() == "guardar":
            orq.guardar_log()
            orq._guardar_snapshot(silencioso=False)

        elif entrada.lower() == "exportar":
            orq.exportar_sesion_md()

        elif entrada.lower() == "verificar":
            print("\n🔍 Ejecutando verificaciones automatizadas de QA...")
            print("─" * 50)
            try:
                informe = informe_qa()
                print(informe)
                # Enviar el informe al agente QA para que lo analice y emita veredicto
                print("\n📨 Enviando informe al @QA para análisis...")
                respuesta = orq.enviar_a_agente(
                    "QA",
                    f"[INFORME AUTOMATIZADO]\n\n{informe}\n\n"
                    "Analiza este informe automatizado. Emite tu veredicto con el formato obligatorio. "
                    "Si hay hallazgos RECHAZADOS, indica al @Programador qué debe corregir.",
                    tarea="verificacion_automatizada",
                )
                print(f"\n💬 @QA responde:")
                print(respuesta)
            except Exception as e:
                print(f"  ❌ Error al ejecutar verificaciones: {e}")

        elif entrada.lower() == "sesiones":
            orq.listar_sesiones()

        elif entrada.lower().startswith("cargar "):
            sid = entrada[7:].strip()
            if sid:
                orq.restaurar_sesion(sid)
            else:
                print("  ⚠️ Formato: cargar <sesion_id> (ej: cargar 20260514_181400)")

        elif entrada.lower() == "ayuda":
            print("\n📖 COMANDOS:")
            print("  @Agente mensaje    -> Enviar mensaje directo")
            print("  flujo mensaje      -> Cadena completa de agentes")
            print("  verificar          -> Verificaciones automatizadas de QA")
            print("  estado             -> Ver agentes + tokens")
            print("  reset @Agente      -> Reiniciar un agente")
            print("  sesiones           -> Listar sesiones guardadas")
            print("  cargar <id>        -> Restaurar sesion anterior")
            print("  exportar           -> Exportar a Markdown")
            print("  guardar            -> Guardar snapshot + log JSON")
            print("  salir              -> Terminar")

        elif entrada.lower().startswith("reset @"):
            nombre = entrada[7:].strip()
            orq.resetear_agente(nombre)

        elif entrada.lower().startswith("flujo "):
            mensaje = entrada[6:].strip()
            orq.ejecutar_flujo("AnalistaNegocio", mensaje, tarea=mensaje[:30])

        elif entrada.startswith("@"):
            # Parsear @Agente mensaje
            match = re.match(r"@(\w+)\s+(.*)", entrada, re.DOTALL)
            if match:
                agente = match.group(1)
                mensaje = match.group(2)
                respuesta = orq.enviar_a_agente(agente, mensaje)
                print(f"\n💬 @{agente} responde:")
                print(respuesta)
            else:
                print("⚠️ Formato: @NombreAgente tu mensaje")

        else:
            print("⚠️ Comando no reconocido. Escribe 'ayuda' para ver los comandos.")


if __name__ == "__main__":
    main()

