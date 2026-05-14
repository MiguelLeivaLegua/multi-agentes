"""
qa_herramientas.py - Herramientas automatizadas para el agente @QA
Autor: @Programador (Lead Developer)

Propósito:
    Proporciona funciones que el @QA puede solicitar ejecutar para validar
    código, seguridad, portabilidad y cumplimiento normativo sin necesidad
    de revisar archivo por archivo manualmente.

Uso desde el orquestador:
    El usuario puede ejecutar: verificar  → corre todas las verificaciones
    O el @QA puede pedir al usuario que ejecute verificaciones específicas.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# ─── Fix encoding para consola de Windows (cp1252 no soporta emojis) ────────
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# Ruta raíz del proyecto: subimos desde src/services/ hasta erp-veterinaria-project/
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent


# ═══════════════════════════════════════════════════════════════
# 1. VERIFICACIÓN DE RUTAS ABSOLUTAS (Portabilidad)
# ═══════════════════════════════════════════════════════════════

def verificar_rutas_absolutas() -> dict:
    """
    Busca rutas absolutas de Windows (C:\\Users, D:\\, etc.) en archivos .py.
    Retorna un dict con 'estado' (APROBADO/RECHAZADO) y 'hallazgos'.
    """
    hallazgos = []
    patron = re.compile(r'[A-Z]:\\\\?(?:Users|Archivos|Program)', re.IGNORECASE)

    for archivo in RAIZ_PROYECTO.rglob("*.py"):
        # Excluir: caché, venvs, y este mismo archivo (contiene la referencia como documentación)
        if "__pycache__" in str(archivo) or ".venv" in str(archivo) or "qa_herramientas" in archivo.name:
            continue
        try:
            contenido = archivo.read_text(encoding="utf-8")
            for i, linea in enumerate(contenido.splitlines(), 1):
                if patron.search(linea) and not linea.strip().startswith("#"):
                    ruta_rel = archivo.relative_to(RAIZ_PROYECTO)
                    hallazgos.append({
                        "archivo": str(ruta_rel),
                        "linea": i,
                        "contenido": linea.strip()[:120],
                    })
        except Exception:
            continue

    return {
        "verificacion": "Rutas absolutas",
        "estado": "RECHAZADO" if hallazgos else "APROBADO",
        "hallazgos": hallazgos,
        "total": len(hallazgos),
    }


# ═══════════════════════════════════════════════════════════════
# 2. VERIFICACIÓN DE SECRETS EXPUESTOS (Seguridad)
# ═══════════════════════════════════════════════════════════════

def verificar_secrets_expuestos() -> dict:
    """
    Busca posibles secrets, API keys, contraseñas en texto plano
    dentro de archivos .py (excluyendo .env que es el lugar correcto).
    """
    hallazgos = []
    patrones = [
        (re.compile(r'(?:api_key|apikey|api[-_]?key)\s*=\s*["\'][^"\']{10,}["\']', re.IGNORECASE), "Posible API Key expuesta"),
        (re.compile(r'(?:password|passwd|pwd|contraseña)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Posible contraseña expuesta"),
        (re.compile(r'(?:secret|token)\s*=\s*["\'][^"\']{10,}["\']', re.IGNORECASE), "Posible secret/token expuesto"),
        (re.compile(r'sk-[a-zA-Z0-9]{20,}', re.IGNORECASE), "Posible API Key (formato sk-...)"),
    ]

    for archivo in RAIZ_PROYECTO.rglob("*.py"):
        if "__pycache__" in str(archivo) or ".venv" in str(archivo):
            continue
        try:
            contenido = archivo.read_text(encoding="utf-8")
            for i, linea in enumerate(contenido.splitlines(), 1):
                # Ignorar comentarios y líneas que leen de os.getenv
                if linea.strip().startswith("#") or "os.getenv" in linea or "environ" in linea:
                    continue
                for patron, descripcion in patrones:
                    if patron.search(linea):
                        ruta_rel = archivo.relative_to(RAIZ_PROYECTO)
                        hallazgos.append({
                            "archivo": str(ruta_rel),
                            "linea": i,
                            "tipo": descripcion,
                            "contenido": linea.strip()[:120],
                        })
        except Exception:
            continue

    return {
        "verificacion": "Secrets expuestos en código",
        "estado": "RECHAZADO" if hallazgos else "APROBADO",
        "hallazgos": hallazgos,
        "total": len(hallazgos),
    }


# ═══════════════════════════════════════════════════════════════
# 3. VERIFICACIÓN DE SQL INSEGURO (Inyección SQL)
# ═══════════════════════════════════════════════════════════════

def verificar_sql_inseguro() -> dict:
    """
    Busca patrones de concatenación de strings en consultas SQL
    que podrían indicar vulnerabilidad a inyección SQL.
    """
    hallazgos = []
    patrones = [
        (re.compile(r'(?:execute|cursor\.execute)\s*\(\s*["\'].*?\%s.*?["\'].*?%', re.IGNORECASE), "Uso de %s en SQL (usar parámetros)"),
        (re.compile(r'(?:execute|cursor\.execute)\s*\(\s*f["\']', re.IGNORECASE), "f-string en SQL (peligro de inyección)"),
        (re.compile(r'(?:execute|cursor\.execute)\s*\(.*?\+.*?(?:input|request|form|args)', re.IGNORECASE), "Concatenación de entrada de usuario en SQL"),
        (re.compile(r'(?:SELECT|INSERT|UPDATE|DELETE).*?\+\s*(?:str\(|f"|f\')', re.IGNORECASE), "Concatenación de string en consulta SQL"),
    ]

    for archivo in RAIZ_PROYECTO.rglob("*.py"):
        if "__pycache__" in str(archivo) or ".venv" in str(archivo) or "test_" in archivo.name:
            continue
        try:
            contenido = archivo.read_text(encoding="utf-8")
            for i, linea in enumerate(contenido.splitlines(), 1):
                if linea.strip().startswith("#"):
                    continue
                for patron, descripcion in patrones:
                    if patron.search(linea):
                        ruta_rel = archivo.relative_to(RAIZ_PROYECTO)
                        hallazgos.append({
                            "archivo": str(ruta_rel),
                            "linea": i,
                            "tipo": descripcion,
                            "contenido": linea.strip()[:120],
                        })
        except Exception:
            continue

    return {
        "verificacion": "SQL inseguro (inyección)",
        "estado": "RECHAZADO" if hallazgos else "APROBADO",
        "hallazgos": hallazgos,
        "total": len(hallazgos),
    }


# ═══════════════════════════════════════════════════════════════
# 4. VERIFICACIÓN DE DEPENDENCIAS (requirements.txt)
# ═══════════════════════════════════════════════════════════════

def verificar_dependencias() -> dict:
    """
    Verifica que todas las importaciones en archivos .py
    tengan su dependencia correspondiente en requirements.txt.
    """
    req_archivo = RAIZ_PROYECTO / "requirements.txt"
    if not req_archivo.exists():
        return {
            "verificacion": "Dependencias (requirements.txt)",
            "estado": "RECHAZADO",
            "hallazgos": [{"tipo": "requirements.txt no existe"}],
            "total": 1,
        }

    # Leer dependencias declaradas
    dependencias = set()
    for linea in req_archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            # Extraer nombre del paquete (antes de >= o ==)
            nombre = re.split(r'[><=!]', linea)[0].strip().lower()
            dependencias.add(nombre)
            # Agregar alias comunes
            if nombre == "python-dotenv":
                dependencias.add("dotenv")
            if nombre == "openai":
                dependencias.add("openai")

    # Paquetes de la librería estándar (no necesitan requirements)
    stdlib = {
        "os", "sys", "re", "json", "time", "signal", "atexit", "datetime",
        "pathlib", "subprocess", "hashlib", "typing", "collections",
        "functools", "itertools", "abc", "io", "math", "random",
        "unittest", "logging", "threading", "socket", "http", "email",
        "csv", "sqlite3", "textwrap", "copy", "enum", "dataclasses",
        "contextlib", "traceback", "warnings", "shutil", "tempfile",
        "glob", "struct", "base64", "uuid",
    }

    # Buscar imports en archivos .py
    imports_externos = set()
    for archivo in RAIZ_PROYECTO.rglob("*.py"):
        if "__pycache__" in str(archivo) or ".venv" in str(archivo):
            continue
        try:
            contenido = archivo.read_text(encoding="utf-8")
            for linea in contenido.splitlines():
                match = re.match(r'^(?:from|import)\s+(\w+)', linea)
                if match:
                    modulo = match.group(1).lower()
                    # Ignorar imports relativos (src, tests, etc.)
                    if modulo not in stdlib and modulo not in ("src", "tests", "docs"):
                        imports_externos.add(modulo)
        except Exception:
            continue

    faltantes = imports_externos - dependencias
    hallazgos = [{"paquete": p, "tipo": "Import no declarado en requirements.txt"} for p in sorted(faltantes)]

    return {
        "verificacion": "Dependencias (requirements.txt)",
        "estado": "RECHAZADO" if hallazgos else "APROBADO",
        "imports_detectados": sorted(imports_externos),
        "dependencias_declaradas": sorted(dependencias),
        "hallazgos": hallazgos,
        "total": len(hallazgos),
    }


# ═══════════════════════════════════════════════════════════════
# 5. VERIFICACIÓN DE ESTRUCTURA DEL PROYECTO
# ═══════════════════════════════════════════════════════════════

def verificar_estructura() -> dict:
    """
    Verifica que la estructura del proyecto esté completa:
    - __init__.py en todos los paquetes
    - Archivos de docs existan
    - .env y .gitignore existan
    """
    hallazgos = []
    archivos_requeridos = {
        "src/__init__.py": "Paquete src no importable",
        "src/api/__init__.py": "Paquete src/api no importable",
        "src/db/__init__.py": "Paquete src/db no importable",
        "src/services/__init__.py": "Paquete src/services no importable",
        "docs/business_rules.md": "Falta documento de reglas de negocio",
        "docs/architecture.md": "Falta documento de arquitectura",
        "docs/CHANGELOG.md": "Falta cronología de cambios",
        ".env": "Falta archivo de variables de entorno",
        ".gitignore": "Falta .gitignore (riesgo de subir secrets)",
        "requirements.txt": "Falta requirements.txt",
        "tests/test_main.py": "Falta archivo de pruebas",
    }

    for ruta_rel, mensaje in archivos_requeridos.items():
        ruta = RAIZ_PROYECTO / ruta_rel
        if not ruta.exists():
            hallazgos.append({"archivo": ruta_rel, "tipo": mensaje})

    return {
        "verificacion": "Estructura del proyecto",
        "estado": "RECHAZADO" if hallazgos else "APROBADO",
        "hallazgos": hallazgos,
        "total": len(hallazgos),
    }


# ═══════════════════════════════════════════════════════════════
# 6. EJECUTAR PYTEST (si está instalado)
# ═══════════════════════════════════════════════════════════════

def ejecutar_pytest() -> dict:
    """
    Ejecuta pytest sobre ./tests/ y captura el resultado.
    Retorna el output completo y el estado (pasó/falló).
    """
    try:
        resultado = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            cwd=str(RAIZ_PROYECTO),
            timeout=60,  # Máx 60s para no quedarse colgado
        )
        exito = resultado.returncode == 0
        return {
            "verificacion": "Ejecución de pytest",
            "estado": "APROBADO" if exito else "RECHAZADO",
            "codigo_salida": resultado.returncode,
            "salida": resultado.stdout[-2000:] if resultado.stdout else "",
            "errores": resultado.stderr[-1000:] if resultado.stderr else "",
        }
    except FileNotFoundError:
        return {
            "verificacion": "Ejecución de pytest",
            "estado": "BLOQUEADO",
            "hallazgos": [{"tipo": "pytest no está instalado. Ejecutar: pip install pytest"}],
        }
    except subprocess.TimeoutExpired:
        return {
            "verificacion": "Ejecución de pytest",
            "estado": "RECHAZADO",
            "hallazgos": [{"tipo": "Los tests tardaron más de 60 segundos (posible cuelgue)"}],
        }


# ═══════════════════════════════════════════════════════════════
# 7. VERIFICACIÓN DE .ENV EN .GITIGNORE
# ═══════════════════════════════════════════════════════════════

def verificar_gitignore() -> dict:
    """
    Verifica que .env esté listado en .gitignore para no subir secrets.
    """
    gitignore = RAIZ_PROYECTO / ".gitignore"
    if not gitignore.exists():
        return {
            "verificacion": ".gitignore protege secrets",
            "estado": "RECHAZADO",
            "hallazgos": [{"tipo": ".gitignore no existe — secrets en riesgo"}],
            "total": 1,
        }

    contenido = gitignore.read_text(encoding="utf-8")
    protegidos = [".env", "*.env"]
    faltantes = [p for p in protegidos if p not in contenido]

    return {
        "verificacion": ".gitignore protege secrets",
        "estado": "RECHAZADO" if faltantes else "APROBADO",
        "hallazgos": [{"tipo": f"'{p}' no está en .gitignore"} for p in faltantes],
        "total": len(faltantes),
    }


# ═══════════════════════════════════════════════════════════════
# INFORME COMPLETO DE QA
# ═══════════════════════════════════════════════════════════════

def generar_informe_completo() -> str:
    """
    Ejecuta TODAS las verificaciones y genera un informe formateado
    que el agente @QA puede usar directamente.
    """
    verificaciones = [
        verificar_estructura(),
        verificar_rutas_absolutas(),
        verificar_secrets_expuestos(),
        verificar_sql_inseguro(),
        verificar_dependencias(),
        verificar_gitignore(),
        ejecutar_pytest(),
    ]

    lineas = [
        "# 🔍 INFORME AUTOMATIZADO DE CALIDAD — ERP Veterinaria",
        f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Verificaciones ejecutadas:** {len(verificaciones)}",
        "",
    ]

    total_aprobados = sum(1 for v in verificaciones if v["estado"] == "APROBADO")
    total_rechazados = sum(1 for v in verificaciones if v["estado"] == "RECHAZADO")
    total_bloqueados = sum(1 for v in verificaciones if v["estado"] == "BLOQUEADO")

    lineas.append(f"## RESUMEN: {total_aprobados} ✅ | {total_rechazados} ❌ | {total_bloqueados} ⏸️")
    lineas.append("")

    for v in verificaciones:
        icono = "✅" if v["estado"] == "APROBADO" else "❌" if v["estado"] == "RECHAZADO" else "⏸️"
        lineas.append(f"### {icono} {v['verificacion']} — {v['estado']}")

        if v.get("hallazgos"):
            for h in v["hallazgos"][:10]:  # Máx 10 hallazgos por verificación
                detalles = " | ".join(f"{k}: {val}" for k, val in h.items())
                lineas.append(f"  - {detalles}")

        if v.get("salida"):
            lineas.append(f"  ```\n{v['salida'][:1500]}\n  ```")

        lineas.append("")

    return "\n".join(lineas)


# ═══════════════════════════════════════════════════════════════
# EJECUCIÓN DIRECTA
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(generar_informe_completo())

