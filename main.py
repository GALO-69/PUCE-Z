#!/usr/bin/env python3
"""
main.py — MONITOR DE RECURSOS DEL SISTEMA
Sistema Operativo: Ubuntu Linux
Requiere Python 3.10+ y privilegios de root.

Uso:
    sudo python3 main.py           # Monitoreo continuo (modo por defecto)
    sudo python3 main.py --clean   # Ejecutar solo limpieza automática (para cron)
    sudo python3 main.py --help    # Mostrar ayuda

Estructura del proyecto:
    system_monitor/
    ├── config/config.py           → Configuración global y umbrales
    ├── controllers/system_cleaner.py → Limpieza automática del sistema
    ├── monitors/resource_monitor.py  → Monitoreo de CPU, RAM, Disco
    ├── monitors/process_manager.py   → Gestión reactiva de procesos pesados
    ├── monitors/ransomware_monitor.py → Anti-ransomware (inotify + extensiones)
    ├── auth/roles.py              → Verificación de privilegios root
    ├── logs/logger.py             → Logger centralizado
    ├── utils/alerts.py            → Alertas visuales en consola
    └── main.py                    → Punto de entrada principal
"""

import sys
import time
import argparse
import signal
import threading

# ── Verificar que el sys.path incluya el directorio del proyecto ──────
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Importaciones internas ────────────────────────────────────────────
from auth.roles import require_root, get_current_user
from logs.logger import logger
from utils.alerts import alert_info, alert_success, alert_critical, alert_warning
from config.config import MONITOR_INTERVAL
import config.config as cfg

from monitors.resource_monitor import ResourceMonitor
from monitors.process_manager import ProcessManager
from monitors.ransomware_monitor import RansomwareMonitor
from controllers.system_cleaner import SystemCleaner


# ─────────────────────────────────────────────────────────────────────
# Manejador de señales para salida limpia
# ─────────────────────────────────────────────────────────────────────

_shutdown_event = threading.Event()


def _signal_handler(signum, frame):
    """Maneja SIGINT y SIGTERM para salida ordenada."""
    logger.info("Señal %d recibida. Iniciando apagado ordenado...", signum)
    alert_warning("Señal de interrupción recibida. Cerrando monitor...")
    _shutdown_event.set()


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ─────────────────────────────────────────────────────────────────────
# Banner de inicio
# ─────────────────────────────────────────────────────────────────────

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║       MONITOR DE RECURSOS DEL SISTEMA — SISTEMAS OPERATIVOS  ║
║       Python 3.10+ │ Ubuntu Linux │ Requiere ROOT            ║
╚══════════════════════════════════════════════════════════════╝
"""


def print_banner():
    print(BANNER)
    logger.info("Sistema de monitoreo iniciado.")


# ─────────────────────────────────────────────────────────────────────
# Modo: Monitoreo continuo
# ─────────────────────────────────────────────────────────────────────

def run_monitor():
    """
    Bucle principal de monitoreo continuo.
    Integra ResourceMonitor, ProcessManager y RansomwareMonitor
    en un ciclo coordinado con exclusión mutua vía cfg.LOCKDOWN.
    """
    resource_monitor = ResourceMonitor()
    process_manager  = ProcessManager()
    ransomware_monitor = RansomwareMonitor()

    # Iniciar RansomwareMonitor en hilo separado (no bloqueante)
    ransomware_thread = ransomware_monitor.start()
    alert_info("Anti-ransomware activo (inotify + barrido de extensiones).")

    cycle = 0
    alert_info(f"Bucle de monitoreo iniciado. Intervalo: {MONITOR_INTERVAL}s")
    logger.info("Bucle principal de monitoreo iniciado.")

    while not _shutdown_event.is_set():
        cycle += 1
        print(f"\n{'═' * 65}")
        alert_info(f"Ciclo #{cycle} — usuario real: {get_current_user()}")

        # ── Lectura de recursos ──────────────────────────────────────
        try:
            stats = resource_monitor.check_once()
            alert_info(
                f"CPU: {stats['cpu_percent']:.1f}% | "
                f"RAM: {stats['ram_percent']:.1f}% ({stats['ram_used_gb']:.2f}GB / {stats['ram_total_gb']:.2f}GB) | "
                f"DISCO: {stats['disk_percent']:.1f}% ({stats['disk_used_gb']:.2f}GB / {stats['disk_total_gb']:.2f}GB)"
            )
        except Exception as e:
            logger.error("Error en ResourceMonitor.check_once(): %s", e, exc_info=True)

        # ── Gestión reactiva de procesos ────────────────────────────
        # Solo si no hay LOCKDOWN activo
        if not cfg.LOCKDOWN:
            try:
                process_manager.check_and_manage()
            except Exception as e:
                logger.error("Error en ProcessManager.check_and_manage(): %s", e, exc_info=True)
        else:
            alert_warning("LOCKDOWN activo — gestión de procesos suspendida este ciclo.")

        # ── Barrido anti-ransomware complementario ──────────────────
        # El inotify ya corre en segundo plano; este barrido es fallback/complementario.
        if not cfg.LOCKDOWN and cycle % 6 == 0:  # Cada 6 ciclos (~30s con intervalo=5)
            try:
                ransomware_monitor.scan_suspicious_files()
            except Exception as e:
                logger.error("Error en barrido anti-ransomware: %s", e, exc_info=True)

        # ── Estado de LOCKDOWN ──────────────────────────────────────
        if cfg.LOCKDOWN:
            alert_warning(
                "⚠  MODO LOCKDOWN ACTIVO — Nuevas escrituras bloqueadas. "
                "Revisa /var/log/system_monitor.log para detalles."
            )

        # ── Esperar hasta el próximo ciclo ──────────────────────────
        _shutdown_event.wait(timeout=MONITOR_INTERVAL)

    # ── Apagado ordenado ─────────────────────────────────────────────
    ransomware_monitor.stop()
    alert_success("Monitor de recursos detenido correctamente.")
    logger.info("Monitor de recursos detenido. Fin del programa.")


# ─────────────────────────────────────────────────────────────────────
# Modo: Limpieza (para cron)
# ─────────────────────────────────────────────────────────────────────

def run_clean():
    """Ejecuta solo la limpieza automática del sistema (modo cron)."""
    alert_info("=== MODO LIMPIEZA AUTOMÁTICA ===")
    logger.info("Iniciando modo limpieza (--clean).")
    cleaner = SystemCleaner()
    cleaner.run_full_cleanup()


# ─────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Monitor de Recursos del Sistema — Sistemas Operativos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  sudo python3 main.py            # Monitoreo continuo\n"
            "  sudo python3 main.py --clean    # Limpieza automática (cron)\n"
        ),
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Ejecutar solo la limpieza automática del sistema (apto para cron)",
    )
    return parser.parse_args()


def main():
    print_banner()

    # 1. Verificar privilegios de root
    require_root()

    # 2. Parsear argumentos
    args = parse_args()

    # 3. Ejecutar el modo solicitado
    if args.clean:
        run_clean()
    else:
        run_monitor()


if __name__ == "__main__":
    main()