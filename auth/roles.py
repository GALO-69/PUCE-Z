"""
auth/roles.py
Módulo de autenticación y roles del sistema.
Verifica que el script se ejecute con privilegios de root (UID 0).
"""

import os
import sys
from logs.logger import logger
from utils.alerts import alert_critical


def require_root() -> None:
    """
    Verifica que el proceso actual se ejecute como root (UID 0).
    Si no es root, registra el error, muestra una alerta y termina el programa.

    Instrucciones de permisos para el archivo principal:
        sudo chown root:root main.py
        sudo chmod 700 main.py

    O para ejecutar temporalmente sin cambiar permisos del archivo:
        sudo python3 main.py
    """
    if os.getuid() != 0:
        msg = (
            "Este sistema requiere privilegios de ROOT para:\n"
            "  - Leer /proc y /var/log\n"
            "  - Enviar señales a procesos del sistema\n"
            "  - Escribir en /var/log/system_monitor.log\n"
            "  - Ejecutar apt clean y limpieza del sistema\n\n"
            "Ejecuta con: sudo python3 main.py\n\n"
            "Para seguridad permanente:\n"
            "  sudo chown root:root main.py\n"
            "  sudo chmod 700 main.py"
        )
        alert_critical("Acceso denegado: se requiere ejecutar como root.")
        logger.critical("Intento de ejecución sin privilegios root. UID=%d", os.getuid())
        print(msg, file=sys.stderr)
        sys.exit(1)

    logger.info("Verificación de roles: ejecutando como root (UID=0). ✓")


def get_current_user() -> str:
    """Retorna el nombre del usuario real (SUDO_USER si aplica, o root)."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        return sudo_user
    return "root"