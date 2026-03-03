"""
controllers/system_cleaner.py
Limpieza automática del sistema:
  - Limpieza de /tmp
  - Eliminación de logs antiguos
  - apt clean
  - Papelera de usuarios
  - Verificación de actualizaciones de seguridad
Compatible con ejecución por cron.
"""

import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import config.config as cfg
from config.config import OLD_LOG_DAYS
from logs.logger import logger
from utils.alerts import alert_info, alert_success, alert_warning, alert_critical


class SystemCleaner:
    """
    Ejecuta tareas de limpieza y mantenimiento del sistema.
    Usa la variable LOCKDOWN para garantizar exclusión mutua:
    mientras se ejecuta la limpieza no se permiten modificaciones externas.
    """

    def __init__(self):
        logger.info("SystemCleaner inicializado.")

    # ──────────────────────────────────────────────────────────────────
    # Limpieza de /tmp
    # ──────────────────────────────────────────────────────────────────

    def clean_tmp(self) -> None:
        """
        Elimina archivos y directorios en /tmp con más de 24 horas de antigüedad.
        Preserva sockets y archivos activos del sistema.
        """
        alert_info("Limpiando /tmp...")
        removed = 0
        errors  = 0
        cutoff  = time.time() - 86400  # 24 horas

        try:
            for entry in os.scandir("/tmp"):
                try:
                    stat = entry.stat(follow_symlinks=False)
                    if stat.st_mtime < cutoff:
                        if entry.is_dir(follow_symlinks=False):
                            shutil.rmtree(entry.path, ignore_errors=True)
                        else:
                            os.remove(entry.path)
                        removed += 1
                        logger.debug("Eliminado de /tmp: %s", entry.path)
                except (PermissionError, FileNotFoundError, OSError) as e:
                    errors += 1
                    logger.warning("No se pudo eliminar %s: %s", entry.path, e)
        except PermissionError as e:
            logger.error("Sin acceso a /tmp: %s", e)
            return

        msg = f"Limpieza /tmp completada. Eliminados: {removed}, errores: {errors}"
        alert_success(msg)
        logger.info(msg)

    # ──────────────────────────────────────────────────────────────────
    # Limpieza de logs antiguos
    # ──────────────────────────────────────────────────────────────────

    def clean_old_logs(self, log_dir: str = "/var/log", days: int = OLD_LOG_DAYS) -> None:
        """
        Elimina archivos de log en 'log_dir' con más de 'days' días de antigüedad.
        Solo elimina archivos .log, .gz, .bz2 (logs rotados comprimidos).
        """
        alert_info(f"Limpiando logs con más de {days} días en '{log_dir}'...")
        removed = 0
        cutoff  = time.time() - (days * 86400)
        extensions = {".log", ".gz", ".bz2", ".xz", ".1", ".2", ".3", ".4", ".5"}

        try:
            for root, dirs, files in os.walk(log_dir):
                for fname in files:
                    if Path(fname).suffix in extensions or fname.endswith(".log"):
                        full_path = os.path.join(root, fname)
                        try:
                            stat = os.stat(full_path)
                            if stat.st_mtime < cutoff:
                                os.remove(full_path)
                                removed += 1
                                logger.debug("Log eliminado: %s", full_path)
                        except (PermissionError, FileNotFoundError, OSError) as e:
                            logger.warning("No se pudo eliminar log '%s': %s", full_path, e)
        except PermissionError as e:
            logger.error("Sin acceso a '%s': %s", log_dir, e)

        msg = f"Limpieza de logs completada. Eliminados: {removed}"
        alert_success(msg)
        logger.info(msg)

    # ──────────────────────────────────────────────────────────────────
    # apt clean
    # ──────────────────────────────────────────────────────────────────

    def apt_clean(self) -> None:
        """
        Ejecuta 'apt clean' y 'apt autoremove --yes' para liberar
        espacio en caché de paquetes.
        """
        alert_info("Ejecutando apt clean...")
        for cmd in [["apt", "clean"], ["apt", "autoremove", "--yes", "-q"]]:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    alert_success(f"'{' '.join(cmd)}' completado.")
                    logger.info("apt: '%s' exitoso.", " ".join(cmd))
                else:
                    alert_warning(f"'{' '.join(cmd)}' retornó código {result.returncode}.")
                    logger.warning(
                        "apt: '%s' código %d. stderr: %s",
                        " ".join(cmd), result.returncode, result.stderr.strip(),
                    )
            except FileNotFoundError:
                logger.error("apt no encontrado. ¿Es un sistema Debian/Ubuntu?")
                alert_warning("apt no disponible en este sistema.")
                break
            except subprocess.TimeoutExpired:
                logger.error("Timeout ejecutando '%s'.", " ".join(cmd))

    # ──────────────────────────────────────────────────────────────────
    # Papelera de usuarios
    # ──────────────────────────────────────────────────────────────────

    def clean_trash(self) -> None:
        """
        Vacía las papeleras de todos los usuarios en /home/*/.local/share/Trash/
        y la papelera de root en /root/.local/share/Trash/.
        """
        alert_info("Vaciando papeleras de usuarios...")
        trash_dirs: List[str] = []

        # Papeleras en /home
        try:
            for user_dir in Path("/home").iterdir():
                trash = user_dir / ".local" / "share" / "Trash"
                if trash.is_dir():
                    trash_dirs.append(str(trash))
        except PermissionError as e:
            logger.warning("No se pudo leer /home: %s", e)

        # Papelera de root
        root_trash = Path("/root/.local/share/Trash")
        if root_trash.is_dir():
            trash_dirs.append(str(root_trash))

        removed_total = 0
        for trash_path in trash_dirs:
            for subdir in ["files", "info", "expunged"]:
                full = os.path.join(trash_path, subdir)
                if os.path.isdir(full):
                    try:
                        for item in os.scandir(full):
                            try:
                                if item.is_dir(follow_symlinks=False):
                                    shutil.rmtree(item.path, ignore_errors=True)
                                else:
                                    os.remove(item.path)
                                removed_total += 1
                            except (PermissionError, FileNotFoundError, OSError):
                                pass
                    except PermissionError:
                        logger.warning("Sin acceso a papelera: %s", full)

        msg = f"Papeleras vaciadas. Ítems eliminados: {removed_total}"
        alert_success(msg)
        logger.info(msg)

    # ──────────────────────────────────────────────────────────────────
    # Revisión de actualizaciones de seguridad
    # ──────────────────────────────────────────────────────────────────

    def check_security_updates(self) -> None:
        """
        Ejecuta 'apt-get --just-print upgrade' y filtra las actualizaciones
        de seguridad disponibles. Solo informa; no instala.
        """
        alert_info("Revisando actualizaciones de seguridad...")
        try:
            # Actualizar índice de paquetes silenciosamente
            subprocess.run(
                ["apt-get", "update", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            # Verificar paquetes de seguridad pendientes
            result = subprocess.run(
                ["apt-get", "--just-print", "upgrade"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            lines = result.stdout.splitlines()
            security_pkgs = [
                line for line in lines
                if "security" in line.lower()
            ]
            if security_pkgs:
                alert_warning(
                    f"{len(security_pkgs)} actualización(es) de seguridad disponible(s)."
                )
                logger.warning(
                    "Actualizaciones de seguridad pendientes (%d): %s",
                    len(security_pkgs),
                    ", ".join(security_pkgs[:5]),
                )
            else:
                alert_success("No hay actualizaciones de seguridad pendientes.")
                logger.info("No hay actualizaciones de seguridad pendientes.")
        except FileNotFoundError:
            logger.error("apt-get no encontrado.")
        except subprocess.TimeoutExpired:
            logger.error("Timeout en revisión de actualizaciones.")

    # ──────────────────────────────────────────────────────────────────
    # Rutina completa (llamada por cron o manualmente)
    # ──────────────────────────────────────────────────────────────────

    def run_full_cleanup(self) -> None:
        """
        Ejecuta la secuencia completa de limpieza.
        Activa LOCKDOWN durante la ejecución para exclusión mutua.

        Configuración de cron (ejecutar diariamente a las 3:00 AM):
            sudo crontab -e
            0 3 * * * /usr/bin/python3 /ruta/al/proyecto/system_monitor/main.py --clean >> /var/log/system_cleaner_cron.log 2>&1
        """
        if cfg.LOCKDOWN:
            alert_warning("LOCKDOWN activo. Limpieza pospuesta.")
            logger.warning("run_full_cleanup: LOCKDOWN activo, se omite la limpieza.")
            return

        # Activar LOCKDOWN durante la limpieza
        cfg.LOCKDOWN = True
        logger.info("Limpieza automática iniciada. LOCKDOWN=True.")
        alert_info("=== LIMPIEZA AUTOMÁTICA DEL SISTEMA INICIADA ===")

        start_time = time.time()
        try:
            self.clean_tmp()
            self.clean_old_logs()
            self.apt_clean()
            self.clean_trash()
            self.check_security_updates()
        except Exception as e:
            logger.error("Error durante la limpieza: %s", e, exc_info=True)
            alert_critical(f"Error en limpieza: {e}")
        finally:
            cfg.LOCKDOWN = False
            elapsed = time.time() - start_time
            msg = f"Limpieza completada en {elapsed:.1f}s. LOCKDOWN=False."
            alert_success(f"=== LIMPIEZA COMPLETADA en {elapsed:.1f}s ===")
            logger.info(msg)