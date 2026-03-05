"""
monitors/resource_monitor.py
Módulo de monitoreo continuo de recursos del sistema: CPU, RAM y Disco.
Umbral crítico: 85%. Si se supera, registra en log, muestra alerta visual
y reporta el usuario que originó el proceso con mayor consumo.
"""

import psutil
import time
from typing import Optional, Tuple

from config.config import (
    CPU_THRESHOLD,
    RAM_THRESHOLD,
    DISK_THRESHOLD,
    MONITOR_INTERVAL,
)
from logs.logger import logger
from utils.alerts import alert_critical, alert_info, alert_warning


class ResourceMonitor:
    """
    Monitorea CPU, RAM y Disco en bucle continuo.
    Al superar el umbral crítico (85%):
      - Registra en /var/log/system_monitor.log
      - Muestra alerta visual en consola
      - Identifica el usuario del proceso que más consume
    """

    def __init__(self):
        self._running = False
        logger.info("ResourceMonitor inicializado. Umbrales → CPU:%d%% RAM:%d%% DISCO:%d%%",
                    CPU_THRESHOLD, RAM_THRESHOLD, DISK_THRESHOLD)

    # ──────────────────────────────────────────────────────────────────
    # Métodos de lectura de recursos
    # ──────────────────────────────────────────────────────────────────

    def get_cpu_usage(self) -> float:
        """Retorna el porcentaje de uso de CPU (promedio de todos los núcleos)."""
        return psutil.cpu_percent(interval=1)

    def get_ram_usage(self) -> Tuple[float, float, float]:
        """
        Retorna (porcentaje_usado, total_GB, usado_GB) de la memoria RAM.
        """
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        used_gb  = mem.used  / (1024 ** 3)
        return mem.percent, total_gb, used_gb

    def get_disk_usage(self, path: str = "/") -> Tuple[float, float, float]:
        """
        Retorna (porcentaje_usado, total_GB, usado_GB) del disco en 'path'.
        """
        disk = psutil.disk_usage(path)
        total_gb = disk.total / (1024 ** 3)
        used_gb  = disk.used  / (1024 ** 3)
        return disk.percent, total_gb, used_gb

    def get_top_cpu_process(self) -> Optional[dict]:
        """
        Identifica el proceso con mayor uso de CPU y retorna su info.
        Retorna dict con: pid, name, cpu_percent, username
        """
        top_proc = None
        top_cpu  = 0.0

        # Primera pasada para inicializar contadores de psutil
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "username"]):
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        time.sleep(0.5)

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "username"]):
            try:
                info = proc.as_dict(attrs=["pid", "name", "cpu_percent", "username"])
                if info["cpu_percent"] and info["cpu_percent"] > top_cpu:
                    top_cpu  = info["cpu_percent"]
                    top_proc = info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return top_proc

    # ──────────────────────────────────────────────────────────────────
    # Lógica de umbrales
    # ──────────────────────────────────────────────────────────────────

    def _check_cpu(self) -> None:
        cpu = self.get_cpu_usage()
        if cpu >= CPU_THRESHOLD:
            top = self.get_top_cpu_process()
            user = top["username"] if top else "desconocido"
            proc = top["name"]     if top else "desconocido"
            msg = (
                f"CPU al {cpu:.1f}% (umbral {CPU_THRESHOLD}%) | "
                f"Proceso top: '{proc}' | Usuario: '{user}'"
            )
            alert_critical(f"CPU CRÍTICA → {msg}")
            logger.critical("RECURSO CPU: %s", msg)
        else:
            alert_info(f"CPU: {cpu:.1f}%")
            logger.debug("CPU: %.1f%%", cpu)

    def _check_ram(self) -> None:
        pct, total, used = self.get_ram_usage()
        if pct >= RAM_THRESHOLD:
            top = self.get_top_cpu_process()
            user = top["username"] if top else "desconocido"
            msg = (
                f"RAM al {pct:.1f}% ({used:.2f}GB / {total:.2f}GB) | "
                f"Usuario proceso top: '{user}'"
            )
            alert_critical(f"RAM CRÍTICA → {msg}")
            logger.critical("RECURSO RAM: %s", msg)
        else:
            alert_info(f"RAM: {pct:.1f}% ({used:.2f}GB / {total:.2f}GB)")
            logger.debug("RAM: %.1f%%", pct)

    def _check_disk(self) -> None:
        pct, total, used = self.get_disk_usage("/")
        if pct >= DISK_THRESHOLD:
            msg = (
                f"DISCO al {pct:.1f}% ({used:.2f}GB / {total:.2f}GB)"
            )
            alert_critical(f"DISCO CRÍTICO → {msg}")
            logger.critical("RECURSO DISCO: %s", msg)
        else:
            alert_info(f"DISCO: {pct:.1f}% ({used:.2f}GB / {total:.2f}GB)")
            logger.debug("DISCO: %.1f%%", pct)

    # ──────────────────────────────────────────────────────────────────
    # Bucle principal de monitoreo
    # ──────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Inicia el bucle continuo de monitoreo.
        Se ejecuta indefinidamente hasta recibir KeyboardInterrupt o
        que _running sea False.
        """
        self._running = True
        logger.info("ResourceMonitor iniciado. Intervalo: %ds.", MONITOR_INTERVAL)
        alert_info(f"Monitor de recursos activo. Intervalo: {MONITOR_INTERVAL}s")

        try:
            while self._running:
                print("\n" + "─" * 60)
                alert_info("Leyendo recursos del sistema...")
                self._check_cpu()
                self._check_ram()
                self._check_disk()
                time.sleep(MONITOR_INTERVAL)
        except KeyboardInterrupt:
            logger.info("ResourceMonitor detenido por el usuario.")
        finally:
            self._running = False

    def stop(self) -> None:
        """Detiene el bucle de monitoreo."""
        self._running = False
        logger.info("ResourceMonitor: señal de parada recibida.")

    def check_once(self) -> dict:
        """
        Ejecuta una sola lectura de recursos y retorna un diccionario
        con los valores actuales. Útil para llamadas desde main.py en
        modo bucle externo.
        """
        cpu = self.get_cpu_usage()
        ram_pct, ram_total, ram_used = self.get_ram_usage()
        disk_pct, disk_total, disk_used = self.get_disk_usage("/")

        result = {
            "cpu_percent":  cpu,
            "ram_percent":  ram_pct,
            "ram_total_gb": ram_total,
            "ram_used_gb":  ram_used,
            "disk_percent": disk_pct,
            "disk_total_gb": disk_total,
            "disk_used_gb":  disk_used,
        }

        # Verificar umbrales y registrar
        if cpu >= CPU_THRESHOLD:
            top = self.get_top_cpu_process()
            user = top["username"] if top else "desconocido"
            proc = top["name"]     if top else "desconocido"
            msg = f"CPU al {cpu:.1f}% | Proceso: '{proc}' | Usuario: '{user}'"
            alert_critical(f"CPU CRÍTICA → {msg}")
            logger.critical("RECURSO CPU: %s", msg)

        if ram_pct >= RAM_THRESHOLD:
            msg = f"RAM al {ram_pct:.1f}% ({ram_used:.2f}GB/{ram_total:.2f}GB)"
            alert_critical(f"RAM CRÍTICA → {msg}")
            logger.critical("RECURSO RAM: %s", msg)

        if disk_pct >= DISK_THRESHOLD:
            msg = f"DISCO al {disk_pct:.1f}% ({disk_used:.2f}GB/{disk_total:.2f}GB)"
            alert_critical(f"DISCO CRÍTICO → {msg}")
            logger.critical("RECURSO DISCO: %s", msg)

        return result