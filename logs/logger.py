"""
logs/logger.py
Módulo de logging centralizado del sistema.
Escribe en /var/log/system_monitor.log y en consola simultáneamente.
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from config.config import LOG_FILE


def setup_logger(name: str = "system_monitor") -> logging.Logger:
    """
    Configura y retorna el logger principal del sistema.
    Utiliza un RotatingFileHandler para evitar que el log crezca indefinidamente.
    También envía la salida a stdout para visibilidad en consola.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        # Evitar duplicar handlers si ya fue configurado
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de archivo con rotación (5 MB, máximo 5 backups)
    try:
        # Intentar crear el archivo de log; requiere permisos de root
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        # Fallback: si no hay permisos, solo loguear en consola
        print(
            f"[ADVERTENCIA] No se puede escribir en {LOG_FILE}. "
            "Ejecuta como root. Usando solo consola.",
            file=sys.stderr,
        )

    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Logger global accesible desde cualquier módulo
logger = setup_logger()