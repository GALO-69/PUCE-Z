"""
monitors/process_manager.py
Gestión reactiva de procesos pesados.
Si un proceso supera el 70% de CPU:
  1. Identifica el PID con mayor consumo.
  2. Valida que NO sea un proceso crítico (lista blanca).
  3. Envía SIGTERM, espera 5 segundos, luego SIGKILL si sigue vivo.
  4. Registra todo en el log.
"""

import os
import signal
import time
import psutil
from typing import Optional

from config.config import (
    CPU_PROCESS_THRESHOLD,
    WHITELIST_PROCESSES,
    SIGTERM_WAIT,
)
from logs.logger import logger
from utils.alerts import alert_critical, alert_warning, alert_info, alert_success


class ProcessManager:
    """
    Monitorea procesos individuales y gestiona reactivamente
    aquellos que superen el umbral de CPU definido.
    """

    def __init__(self):
        logger.info(
            "ProcessManager inicializado. Umbral CPU por proceso: %d%%",
            CPU_PROCESS_THRESHOLD,
        )

    # ──────────────────────────────────────────────────────────────────
    # Identificación del proceso más pesado
    # ──────────────────────────────────────────────────────────────────

    def get_heaviest_process(self) -> Optional[psutil.Process]:
        """
        Retorna el objeto psutil.Process con mayor uso de CPU,
        excluyendo procesos en la lista blanca.
        Realiza dos muestras con intervalo de 1 segundo para
        calcular correctamente el porcentaje.
        """
        # Inicializar contadores
        candidates = []
        for proc in psutil.process_iter(["pid", "name", "username"]):
            try:
                proc.cpu_percent(interval=None)
                candidates.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        time.sleep(1.0)

        top_proc  = None
        top_cpu   = 0.0

        for proc in candidates:
            try:
                cpu = proc.cpu_percent(interval=None)
                name = proc.name()

                # Excluir lista blanca
                if any(wl.lower() in name.lower() for wl in WHITELIST_PROCESSES):
                    continue

                if cpu > top_cpu:
                    top_cpu  = cpu
                    top_proc = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if top_proc and top_cpu >= CPU_PROCESS_THRESHOLD:
            return top_proc
        return None

    # ──────────────────────────────────────────────────────────────────
    # Validación de lista blanca
    # ──────────────────────────────────────────────────────────────────

    def is_whitelisted(self, process: psutil.Process) -> bool:
        """
        Verifica si el proceso está en la lista blanca de procesos críticos.
        También excluye el propio PID del script en ejecución.
        """
        try:
            name = process.name().lower()
            # Verificar contra lista blanca
            for wl in WHITELIST_PROCESSES:
                if wl.lower() in name:
                    return True
            # Verificar si es el propio proceso
            if process.pid == os.getpid():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return False

    # ──────────────────────────────────────────────────────────────────
    # Secuencia de señales: SIGTERM → SIGKILL
    # ──────────────────────────────────────────────────────────────────

    def terminate_process(self, process: psutil.Process) -> bool:
        """
        Aplica la secuencia de terminación:
          1. SIGTERM (kill -15): solicitud amigable de terminación.
          2. Espera SIGTERM_WAIT segundos.
          3. Si sigue vivo: SIGKILL (kill -9): terminación forzada.

        Retorna True si el proceso fue terminado con éxito, False en caso contrario.
        """
        pid  = process.pid
        name = process.name() if process.is_running() else "desconocido"

        try:
            cpu = process.cpu_percent(interval=0.1)
            user = process.username()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            cpu  = 0.0
            user = "desconocido"

        logger.warning(
            "PROCESO PESADO DETECTADO → PID:%d nombre:'%s' CPU:%.1f%% usuario:'%s'",
            pid, name, cpu, user,
        )
        alert_warning(
            f"Proceso pesado detectado → PID:{pid} '{name}' CPU:{cpu:.1f}%% usuario:'{user}'"
        )

        # ── Fase 1: SIGTERM ──────────────────────────────────────────
        try:
            logger.info("Enviando SIGTERM (kill -15) a PID:%d '%s'", pid, name)
            alert_info(f"Enviando SIGTERM a PID:{pid} '{name}'...")
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            logger.info("PID:%d ya no existe al enviar SIGTERM.", pid)
            return True
        except PermissionError:
            logger.error("Sin permisos para enviar señal a PID:%d", pid)
            return False

        # ── Espera ───────────────────────────────────────────────────
        logger.info("Esperando %ds tras SIGTERM para PID:%d...", SIGTERM_WAIT, pid)
        time.sleep(SIGTERM_WAIT)

        # ── Verificar si sigue vivo ──────────────────────────────────
        try:
            still_alive = process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            still_alive = False

        if not still_alive:
            logger.info("PID:%d '%s' terminado correctamente con SIGTERM.", pid, name)
            alert_success(f"PID:{pid} '{name}' terminado con SIGTERM.")
            return True

        # ── Fase 2: SIGKILL ──────────────────────────────────────────
        try:
            logger.warning(
                "PID:%d '%s' sigue activo tras SIGTERM. Enviando SIGKILL (kill -9).",
                pid, name,
            )
            alert_critical(f"PID:{pid} '{name}' sigue activo. Enviando SIGKILL...")
            os.kill(pid, signal.SIGKILL)
            logger.warning("SIGKILL enviado a PID:%d '%s'.", pid, name)
            alert_success(f"SIGKILL enviado a PID:{pid} '{name}'.")
            return True
        except ProcessLookupError:
            logger.info("PID:%d desapareció antes del SIGKILL.", pid)
            return True
        except PermissionError:
            logger.error("Sin permisos para SIGKILL a PID:%d", pid)
            return False

    # ──────────────────────────────────────────────────────────────────
    # Punto de entrada principal
    # ──────────────────────────────────────────────────────────────────

    def check_and_manage(self) -> None:
        """
        Comprueba si existe algún proceso que supere el umbral de CPU
        y, si no está en la lista blanca, lo termina.
        Debe llamarse periódicamente desde el bucle principal.
        """
        proc = self.get_heaviest_process()
        if proc is None:
            logger.debug("Ningún proceso supera el umbral de CPU (%d%%).", CPU_PROCESS_THRESHOLD)
            return

        if self.is_whitelisted(proc):
            logger.info(
                "Proceso PID:%d '%s' está en lista blanca. Se omite.",
                proc.pid, proc.name(),
            )
            return

        self.terminate_process(proc)