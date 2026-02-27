"""
config/config.py
Configuración global del sistema de monitoreo.
Define umbrales, rutas y parámetros de comportamiento.
"""

import os

# ─── Umbrales de recursos ───────────────────────────────────────────
CPU_THRESHOLD = 85          # % crítico de CPU (monitoreo)
RAM_THRESHOLD = 85          # % crítico de RAM
DISK_THRESHOLD = 85         # % crítico de disco

CPU_PROCESS_THRESHOLD = 70  # % para gestión reactiva de procesos

# ─── Rutas del sistema ──────────────────────────────────────────────
LOG_FILE = "/var/log/system_monitor.log"
MONITOR_DIRS = ["/home", "/tmp"]          # Directorios vigilados por anti-ransomware
TMP_DIR = "/tmp"

# ─── Intervalos de tiempo (segundos) ────────────────────────────────
MONITOR_INTERVAL = 5         # Intervalo de lectura de recursos
INOTIFY_BURST_WINDOW = 10    # Ventana de detección de ráfagas (segundos)
INOTIFY_BURST_THRESHOLD = 50 # Número de eventos en la ventana para detectar ráfaga
SIGTERM_WAIT = 5             # Segundos de espera tras SIGTERM antes de SIGKILL

# ─── Lista blanca de procesos críticos ─────────────────────────────
WHITELIST_PROCESSES = {
    "systemd",
    "gnome-shell",
    "Xorg",
    "kthreadd",
    "migration",
    "rcu_sched",
    "watchdog",
    "ksoftirqd",
    "kworker",
    "irq",
    "python3",   # el propio script
    "python",
}

# ─── Extensiones sospechosas de ransomware ──────────────────────────
RANSOMWARE_EXTENSIONS = {
    ".locked",
    ".enc",
    ".crypted",
    ".encrypted",
    ".crypt",
    ".zzzzz",
    ".locky",
    ".zepto",
}

# ─── Estado global de bloqueo ───────────────────────────────────────
# Esta variable es importada y modificada por los módulos que requieren
# exclusión mutua durante análisis críticos.
LOCKDOWN = False

# ─── Logs antiguos (días) ────────────────────────────────────────────
OLD_LOG_DAYS = 30