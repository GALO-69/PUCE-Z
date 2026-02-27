"""
utils/alerts.py
Módulo de alertas visuales en consola.
Proporciona mensajes coloreados para distintos niveles de severidad.
"""

import sys
from datetime import datetime


# Códigos ANSI para colores en terminal
class Colors:
    RESET   = "\033[0m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    GREEN   = "\033[92m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    BG_RED  = "\033[41m"


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def alert_critical(message: str) -> None:
    """Alerta roja para situaciones críticas (umbral superado, ransomware)."""
    print(
        f"{Colors.BG_RED}{Colors.BOLD}[CRÍTICO] {_timestamp()} → {message}{Colors.RESET}",
        file=sys.stdout,
        flush=True,
    )


def alert_warning(message: str) -> None:
    """Alerta amarilla para advertencias de recursos."""
    print(
        f"{Colors.YELLOW}{Colors.BOLD}[ALERTA]  {_timestamp()} → {message}{Colors.RESET}",
        flush=True,
    )


def alert_info(message: str) -> None:
    """Mensaje informativo en cian."""
    print(
        f"{Colors.CYAN}[INFO]    {_timestamp()} → {message}{Colors.RESET}",
        flush=True,
    )


def alert_success(message: str) -> None:
    """Mensaje de éxito en verde."""
    print(
        f"{Colors.GREEN}[OK]      {_timestamp()} → {message}{Colors.RESET}",
        flush=True,
    )


def alert_lockdown(message: str) -> None:
    """Alerta especial para modo LOCKDOWN."""
    print(
        f"{Colors.MAGENTA}{Colors.BOLD}[LOCKDOWN] {_timestamp()} → {message}{Colors.RESET}",
        file=sys.stdout,
        flush=True,
    )