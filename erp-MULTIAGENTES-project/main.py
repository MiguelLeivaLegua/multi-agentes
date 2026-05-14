"""
main.py - Punto de entrada del ERP Veterinaria
Autor: @Programador (Lead Developer)
Descripción: Inicializa la aplicación y carga la configuración desde variables de entorno.
"""

import os
from dotenv import load_dotenv

# Cargamos variables de entorno desde archivo .env (nunca hardcoded)
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "eleam_erp")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def main():
    """Punto de entrada principal del ERP Veterinaria."""
    print("=" * 50)
    print("  ERP Veterinaria - Sistema de Gestión Clínica")
    print("  Centro de Adultos Mayores")
    print("=" * 50)
    print(f"[INFO] Conectando a base de datos: {DB_HOST}/{DB_NAME}")
    # TODO: @Arquitecto debe aprobar el diseño antes de implementar módulos aquí
    # TODO: Importar y registrar rutas desde ./src/api/

if __name__ == "__main__":
    main()

