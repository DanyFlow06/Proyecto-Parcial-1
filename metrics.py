"""
metrics.py
==========
Recopilacion y presentacion de las 9 metricas obligatorias del simulador SO.
Consume datos de los managers (MemoryManager, ResourceManager, FileManager)
y del detector de deadlocks para generar la tabla final de resultados.

Sprint 3 - Daniel
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from logger import log_info

console = Console()


class MetricsCollector:
    """
    Recopila y presenta las metricas obligatorias del simulador.
    Extrae datos directamente de los managers y procesos existentes.
    """

    def __init__(self):
        # ── 9 metricas obligatorias ────────────────────────────────────────────
        self.total_procesos = 0
        self.terminados = 0
        self.bloqueados_residuales = 0
        self.pico_memoria = 0
        self.total_solicitudes_recursos = 0
        self.frecuencia_espera = 0
        self.deadlocks_detectados = 0
        self.deadlocks_resueltos = 0
        self.recursos_en_deadlock = []

        # ── Balance de liberacion final ────────────────────────────────────────
        self.recursos_liberados_final = 0
        self.recursos_retenidos_final = 0

    def recopilar(self, processes, memory_manager, resource_manager=None, deadlock_info=None):
        """
        Escanea todos los managers y procesos para calcular las 9 metricas.

        Parametros:
            processes (list[Process]):       Lista de procesos del escenario.
            memory_manager (MemoryManager):  Administrador de memoria.
            resource_manager (opcional):     Administrador de recursos (puede ser None).
            deadlock_info (dict, opcional):   Informacion del detector de deadlocks.
                Formato esperado:
                {
                    "detectados": int,
                    "resueltos": int,
                    "recursos": list[str]
                }
        """
        # ── 1. Total de procesos simulados ─────────────────────────────────────
        self.total_procesos = len(processes)

        # ── 2 y 3. Procesos terminados y bloqueados ───────────────────────────
        self.terminados = 0
        self.bloqueados_residuales = 0
        for p in processes:
            if p.state == "TERMINADO":
                self.terminados += 1
            elif p.state in ("ESPERANDO", "BLOQUEADO"):
                self.bloqueados_residuales += 1

        # ── 4. Pico maximo de memoria ──────────────────────────────────────────
        self.pico_memoria = memory_manager.peak_memory_used

        # ── 5 y 6. Solicitudes y esperas de recursos ──────────────────────────
        if resource_manager is not None:
            try:
                status = resource_manager.get_status()
                metrics_rm = status.get("metrics", {})
                self.total_solicitudes_recursos = metrics_rm.get("total_requests", 0)
                self.frecuencia_espera = metrics_rm.get("wait_transitions", 0)
            except Exception:
                self.total_solicitudes_recursos = 0
                self.frecuencia_espera = 0
        else:
            self.total_solicitudes_recursos = 0
            self.frecuencia_espera = 0

        # ── 7 y 8. Deadlocks detectados / resueltos / recursos ────────────────
        if deadlock_info is not None:
            self.deadlocks_detectados = deadlock_info.get("detectados", 0)
            self.deadlocks_resueltos = deadlock_info.get("resueltos", 0)
            self.recursos_en_deadlock = deadlock_info.get("recursos", [])
        else:
            self.deadlocks_detectados = 0
            self.deadlocks_resueltos = 0
            self.recursos_en_deadlock = []

        # ── 9. Balance de liberacion final ─────────────────────────────────────
        self.recursos_retenidos_final = 0
        for p in processes:
            self.recursos_retenidos_final += len(p.resources_held)

        if resource_manager is not None:
            try:
                status = resource_manager.get_status()
                total_released = status.get("metrics", {}).get("total_releases", 0)
                self.recursos_liberados_final = total_released
            except Exception:
                self.recursos_liberados_final = 0
        else:
            self.recursos_liberados_final = 0

        log_info(
            f"Metricas recopiladas: {self.total_procesos} procesos, "
            f"{self.terminados} terminados, {self.bloqueados_residuales} bloqueados, "
            f"pico RAM={self.pico_memoria} MB"
        )

    def mostrar_tabla_metricas(self):
        """
        Renderiza una tabla Rich con las 9 metricas obligatorias.
        Colorea valores segun estado: verde = OK, rojo = alerta, amarillo = atencion.
        """
        table = Table(
            title="Metricas Finales del Simulador",
            box=box.HEAVY_HEAD,
            header_style="bold magenta",
            show_lines=True,
        )

        table.add_column("#", style="bold dim", justify="center", width=3)
        table.add_column("Metrica", style="bold", justify="left")
        table.add_column("Valor", justify="center")
        table.add_column("Detalle", justify="left")

        # ── 1. Total procesos ──────────────────────────────────────────────────
        table.add_row(
            "1",
            "Total de procesos simulados",
            f"[cyan]{self.total_procesos}[/cyan]",
            "Conteo global del escenario",
        )

        # ── 2. Terminados ──────────────────────────────────────────────────────
        color_term = "green" if self.terminados == self.total_procesos else "yellow"
        table.add_row(
            "2",
            "Procesos terminados exitosamente",
            f"[{color_term}]{self.terminados}[/{color_term}]",
            f"{self.terminados}/{self.total_procesos} completaron sus instrucciones",
        )

        # ── 3. Bloqueados residuales ───────────────────────────────────────────
        color_bloq = "green" if self.bloqueados_residuales == 0 else "red"
        table.add_row(
            "3",
            "Procesos bloqueados residuales",
            f"[{color_bloq}]{self.bloqueados_residuales}[/{color_bloq}]",
            "Procesos en estado ESPERANDO o BLOQUEADO al cierre",
        )

        # ── 4. Pico de memoria ─────────────────────────────────────────────────
        table.add_row(
            "4",
            "Pico maximo de memoria consumida",
            f"[cyan]{self.pico_memoria} MB[/cyan]",
            "Valor historico maximo registrado en MemoryManager",
        )

        # ── 5. Total solicitudes ───────────────────────────────────────────────
        table.add_row(
            "5",
            "Total de solicitudes de recursos",
            f"[cyan]{self.total_solicitudes_recursos}[/cyan]",
            "Operaciones request_resource acumuladas",
        )

        # ── 6. Frecuencia de espera ────────────────────────────────────────────
        color_esp = "green" if self.frecuencia_espera == 0 else "yellow"
        table.add_row(
            "6",
            "Frecuencia de espera de procesos",
            f"[{color_esp}]{self.frecuencia_espera}[/{color_esp}]",
            "Transiciones al estado ESPERANDO",
        )

        # ── 7. Deadlocks detectados vs resueltos ──────────────────────────────
        if self.deadlocks_detectados == 0:
            color_dl = "green"
            detalle_dl = "Sin interbloqueos"
        elif self.deadlocks_resueltos >= self.deadlocks_detectados:
            color_dl = "yellow"
            detalle_dl = "Todos los deadlocks fueron resueltos"
        else:
            color_dl = "red"
            detalle_dl = f"{self.deadlocks_detectados - self.deadlocks_resueltos} deadlocks sin resolver"

        table.add_row(
            "7",
            "Interbloqueos detectados vs. resueltos",
            f"[{color_dl}]{self.deadlocks_detectados} / {self.deadlocks_resueltos}[/{color_dl}]",
            detalle_dl,
        )

        # ── 8. Recursos en deadlock ────────────────────────────────────────────
        if self.recursos_en_deadlock:
            recursos_str = ", ".join(self.recursos_en_deadlock)
            color_res = "red"
        else:
            recursos_str = "Ninguno"
            color_res = "green"

        table.add_row(
            "8",
            "Recursos involucrados en deadlocks",
            f"[{color_res}]{recursos_str}[/{color_res}]",
            "Recursos identificados en ciclos del RAG",
        )

        # ── 9. Balance de liberacion ───────────────────────────────────────────
        if self.recursos_retenidos_final == 0:
            color_bal = "green"
            detalle_bal = "Sin fugas: todos los recursos fueron devueltos"
        else:
            color_bal = "red"
            detalle_bal = f"{self.recursos_retenidos_final} recurso(s) aun retenidos al cierre"

        table.add_row(
            "9",
            "Balance de liberacion final",
            f"[{color_bal}]Liberados: {self.recursos_liberados_final} | Retenidos: {self.recursos_retenidos_final}[/{color_bal}]",
            detalle_bal,
        )

        console.print()
        console.print(table)
        console.print()

    def get_dict(self):
        """
        Retorna las metricas como diccionario plano.
        Util para exportacion o consumo desde simulator.py.
        """
        return {
            "total_procesos": self.total_procesos,
            "terminados": self.terminados,
            "bloqueados_residuales": self.bloqueados_residuales,
            "pico_memoria_mb": self.pico_memoria,
            "total_solicitudes_recursos": self.total_solicitudes_recursos,
            "frecuencia_espera": self.frecuencia_espera,
            "deadlocks_detectados": self.deadlocks_detectados,
            "deadlocks_resueltos": self.deadlocks_resueltos,
            "recursos_en_deadlock": self.recursos_en_deadlock,
            "recursos_liberados_final": self.recursos_liberados_final,
            "recursos_retenidos_final": self.recursos_retenidos_final,
        }
