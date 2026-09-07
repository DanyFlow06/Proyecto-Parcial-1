"""
main.py
=======
Punto de entrada principal y menu interactivo del Simulador de Micro-Kernel SO.
Integra y coordina los modulos de todo el equipo:
- Modelado de Procesos y Estados (process.py)
- Administrador de Memoria RAM (managers/memory_manager.py)
- Administrador de Recursos y Dispositivos (managers/resource_manager.py)
- Administrador de Archivos Virtuales (managers/file_manager.py)
- Detector de Interbloqueos y Condiciones de Coffman (deadlock_detector.py)
- Estrategia de Evasion con Algoritmo del Banquero (banker_strategy.py)
- Interfaz Enriquecida de Terminal (cli_interface.py)
- Recopilacion y Renderizado de Metricas (metrics.py)
- Visualizacion Grafica RAG con NetworkX/Matplotlib (visualization.py)
- Monitoreo de Hardware Real con psutil (monitoring.py)

Sprint 4 - Daniel (Integracion, Blindaje & README)
"""

import sys
import os
import glob
import json
import argparse
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

from process import Process, ESTADO_ACTIVO_O_LISTO, ESTADO_ESPERANDO, ESTADO_BLOQUEADO, ESTADO_TERMINADO
from logger import log_info, log_warning, log_error
from managers.memory_manager import MemoryManager
from managers.resource_manager import ResourceManager
from managers.file_manager import FileManager
from deadlock_detector import DeadlockDetector
from banker_strategy import BankerStrategy
from metrics import MetricsCollector
import cli_interface as ui

try:
    from visualization import render_rag
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False
    render_rag = None

console = Console()


class SystemSimulatorEngine:
    """
    Motor integral de simulacion del Micro-Kernel SO.
    Gestiona el ciclo de vida de los procesos, asignacion de memoria, peticiones
    de recursos exclusivos/compartidos, operaciones de E/S de archivos,
    deteccion de interbloqueos de Coffman y algoritmo de evasion del Banquero.
    """

    def __init__(self, use_banker: bool = False):
        self.use_banker: bool = use_banker
        self.memory_manager: Optional[MemoryManager] = None
        self.resource_manager: Optional[ResourceManager] = None
        self.file_manager: Optional[FileManager] = None
        self.deadlock_detector: DeadlockDetector = DeadlockDetector()
        self.banker_strategy: BankerStrategy = BankerStrategy()
        self.metrics_collector: MetricsCollector = MetricsCollector()
        
        self.processes: List[Process] = []
        self.current_scenario_path: Optional[str] = None
        self.raw_data: Optional[Dict[str, Any]] = None
        self._last_process_index: int = -1
        
        # Telemetria de interbloqueos
        self.deadlock_history = {
            "detectados": 0,
            "resueltos": 0,
            "recursos": set(),
            "last_detection": None
        }

    def load_scenario(self, filepath: str) -> bool:
        """
        Carga y valida dinamicamente cualquier archivo de escenario JSON.
        No asume nombres fijos de procesos ni recursos (blindaje contra escenario sorpresa).
        """
        if not os.path.exists(filepath):
            console.print(f"[red]Error: No se encontro el archivo '{filepath}'.[/red]")
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validacion estructural
            required = ["total_memory", "resources", "processes"]
            for field in required:
                if field not in data:
                    raise ValueError(f"Falta el campo obligatorio '{field}' en el JSON.")

            if not isinstance(data["resources"], list):
                raise ValueError("'resources' debe ser una lista de recursos.")
            if not isinstance(data["processes"], list):
                raise ValueError("'processes' debe ser una lista de procesos.")

            # Inicializar Subsistemas / Managers
            self.memory_manager = MemoryManager(data["total_memory"])
            self.resource_manager = ResourceManager(data["resources"])
            self.file_manager = FileManager()
            self.banker_strategy = BankerStrategy()
            self.processes = []
            self.deadlock_history = {
                "detectados": 0,
                "resueltos": 0,
                "recursos": set(),
                "last_detection": None
            }

            # Carga dinamica de procesos
            for p_data in data["processes"]:
                pid = str(p_data.get("pid", f"P_{len(self.processes)+1}"))
                mem = int(p_data.get("memory_required", 0))
                instructions = list(p_data.get("instructions", []))

                p = Process(pid=pid, memory_required=mem, instructions=instructions)
                
                # Intentar asignar memoria inicial al proceso
                allocated = self.memory_manager.allocate_memory(p)
                if not allocated:
                    log_warning(f"Proceso {pid} puesto en ESPERANDO: Memoria RAM insuficiente ({mem} MB requeridos).")

                self.processes.append(p)

            self.current_scenario_path = filepath
            self.raw_data = data
            self._last_process_index = -1

            console.print(
                f"[green]Escenario cargado exitosamente: [bold]{os.path.basename(filepath)}[/bold] "
                f"({len(self.processes)} procesos, {len(self.resource_manager.resources)} recursos, "
                f"RAM: {self.memory_manager.total_memory} MB)[/green]"
            )
            log_info(f"Escenario '{filepath}' cargado con exito.")
            return True

        except json.JSONDecodeError as jde:
            console.print(f"[red]Error: Formato JSON invalido en '{filepath}': {jde}[/red]")
            log_error(f"Error JSONDecodeError: {jde}")
            return False
        except Exception as ex:
            console.print(f"[red]Error de validacion al cargar escenario: {ex}[/red]")
            log_error(f"Error al cargar escenario: {ex}")
            return False

    def step(self, verbose: bool = True) -> bool:
        """
        Ejecuta exactamente un paso discreto (tick) en el micro-kernel.
        Retorna True si algun proceso pudo ejecutar una accion, False si el sistema se detuvo.
        """
        if not self.processes:
            if verbose:
                console.print("[yellow]No hay procesos cargados para simular.[/yellow]")
            return False

        # 1. Intentar despertar procesos en ESPERANDO por memoria
        for p in self.processes:
            if p.state == ESTADO_ESPERANDO and p.memory_required > 0 and p.pid not in self._pids_waiting_resources():
                if self.memory_manager.allocate_memory(p):
                    log_info(f"Proceso {p.pid} obtuvo memoria RAM ({p.memory_required} MB) y pasa a LISTO.")

        progress_made = False

        # 2. Iterar procesos activos con planificacion Round-Robin
        n = len(self.processes)
        for i in range(n):
            idx = (self._last_process_index + 1 + i) % n
            process = self.processes[idx]
            if process.state == ESTADO_ACTIVO_O_LISTO and process.pending_actions:
                self._last_process_index = idx
                action = process.pending_actions.pop(0)
                action_type = action.get("action")
                target = action.get("resource") or action.get("file")
                units = int(action.get("units", 1))

                msg_step = f"Proceso [bold cyan]{process.pid}[/bold cyan] ejecuta [bold]{action_type}[/bold] -> [yellow]{target}[/yellow]"
                if verbose:
                    console.print(f"  -> {msg_step}")
                log_info(f"Step PID={process.pid}: {action_type} target={target} units={units}")

                # Operaciones de Recursos
                if action_type == "request_resource":
                    if self.use_banker:
                        granted = self.banker_strategy.request_resource_safe(
                            resource_name=target,
                            process=process,
                            processes=self.processes,
                            resource_manager=self.resource_manager,
                            units=units
                        )
                        if not granted and verbose:
                            console.print(f"    [dim magenta]Banquero: Solicitud de {process.pid} demorada por precaucion de Estado Seguro.[/dim magenta]")
                    else:
                        self.resource_manager.request_resource(target, process, units)

                elif action_type == "release_resource":
                    self.resource_manager.release_resource(target, process, units)

                # Operaciones de Archivos
                elif action_type == "create_file":
                    self.file_manager.create_file(target, process.pid)
                elif action_type == "write_file":
                    content = action.get("content", f"Datos del proceso {process.pid}")
                    self.file_manager.write_file(target, process.pid, content)
                elif action_type == "read_file":
                    self.file_manager.read_file(target, process.pid)
                elif action_type == "move_file":
                    new_name = action.get("new_name", f"{target}.bak")
                    self.file_manager.move_file(target, new_name, process.pid)
                elif action_type == "delete_file":
                    self.file_manager.delete_file(target, process.pid)
                else:
                    log_warning(f"Accion desconocida '{action_type}' para PID={process.pid}.")

                progress_made = True

                # Comprobar terminacion
                if not process.pending_actions and process.state == ESTADO_ACTIVO_O_LISTO:
                    self._terminate_process(process)

                break

        # 3. Evaluacion programatica de Interbloqueos (Coffman)
        detection = self.deadlock_detector.detect_deadlock(self.processes, self.resource_manager)
        if detection["has_deadlock"]:
            self.deadlock_history["detectados"] += 1
            for r in detection["deadlocked_resources"]:
                self.deadlock_history["recursos"].add(r)
            self.deadlock_history["last_detection"] = detection
            if verbose:
                console.print(
                    f"    [bold red]ALERTA DEADLOCK: Procesos: "
                    f"{detection['deadlocked_pids']} | Recursos: {detection['deadlocked_resources']}[/bold red]"
                )

        return progress_made

    def _pids_waiting_resources(self) -> List[str]:
        pids = []
        if self.resource_manager:
            for queue in self.resource_manager.waiting_queue.values():
                for entry in queue:
                    pids.append(entry["process"].pid)
        return pids

    def _terminate_process(self, process: Process):
        for r_name in list(process.resources_held):
            self.resource_manager.release_resource(r_name, process)

        self.memory_manager.release_memory(process)
        process.change_state(ESTADO_TERMINADO)
        log_info(f"Proceso {process.pid} finalizado exitosamente. Recursos y RAM devueltos.")

    def run_all(self, max_ticks: int = 200, verbose: bool = True) -> Dict[str, Any]:
        ticks = 0
        if verbose:
            mode_name = "[bold magenta]CON Algoritmo del Banquero[/bold magenta]" if self.use_banker else "[bold cyan]SIN Banquero (Deteccion Pura)[/bold cyan]"
            console.print(f"\n[bold]Iniciando Modo Automatico {mode_name}...[/bold]")

        while ticks < max_ticks:
            ticks += 1
            progress = self.step(verbose=verbose)
            if not progress:
                unfinished = [p for p in self.processes if not p.is_finished()]
                if unfinished:
                    log_warning(f"Simulacion detenida en tick {ticks}. Incompletos: {[p.pid for p in unfinished]}")
                break

        final_detection = self.deadlock_detector.detect_deadlock(self.processes, self.resource_manager)
        if final_detection["has_deadlock"]:
            self.deadlock_history["detectados"] = max(self.deadlock_history["detectados"], 1)
            for r in final_detection["deadlocked_resources"]:
                self.deadlock_history["recursos"].add(r)
            self.deadlock_history["last_detection"] = final_detection

        deadlock_info = {
            "detectados": self.deadlock_history["detectados"],
            "resueltos": self.banker_strategy.avoided_deadlocks_count if self.use_banker else 0,
            "recursos": sorted(list(self.deadlock_history["recursos"]))
        }

        self.metrics_collector.recopilar(
            processes=self.processes,
            memory_manager=self.memory_manager,
            resource_manager=self.resource_manager,
            deadlock_info=deadlock_info
        )

        return self.metrics_collector.get_dict()

    def show_rag_visualization(self):
        if not HAS_VISUALIZATION:
            console.print("[yellow]Matplotlib/NetworkX no estan disponibles para visualizacion grafica.[/yellow]")
            return

        if not self.processes or not self.resource_manager:
            console.print("[yellow]No hay procesos o recursos cargados para generar el grafo.[/yellow]")
            return

        pids = [p.pid for p in self.processes]
        held = {p.pid: list(p.resources_held) for p in self.processes}
        waiting = {}
        for r_name, q in self.resource_manager.waiting_queue.items():
            for entry in q:
                pid = entry["process"].pid
                waiting.setdefault(pid, []).append(r_name)

        deadlock_cycle = []
        if self.deadlock_history.get("last_detection"):
            deadlock_cycle = self.deadlock_history["last_detection"].get("deadlock_edges", [])

        console.print("[cyan]Renderizando Grafo RAG interactivo... Cierra la ventana para continuar.[/cyan]")
        render_rag(pids, held, waiting, deadlock_cycle)


def listar_escenarios_disponibles() -> List[str]:
    directorio = os.path.join(os.path.dirname(__file__), "scenarios")
    if not os.path.exists(directorio):
        return []
    return sorted(glob.glob(os.path.join(directorio, "*.json")))


def menu_interactivo():
    engine = SystemSimulatorEngine(use_banker=False)
    escenario_actual = None

    while True:
        opcion = ui.mostrar_menu_principal()

        if opcion == "1":
            escenarios = listar_escenarios_disponibles()
            console.print("\n[bold cyan]Escenarios disponibles en scenarios/:[/bold cyan]")
            for idx, ruta in enumerate(escenarios, 1):
                nombre = os.path.basename(ruta)
                console.print(f"  [bold]{idx}.[/bold] {nombre}")
            console.print(f"  [bold]C.[/bold] Cargar archivo JSON personalizado / Escenario Sorpresa")

            eleccion = Prompt.ask("\nSelecciona un numero o 'C'", default="1")
            
            if eleccion.upper() == "C":
                ruta_custom = Prompt.ask("Ingresa la ruta del archivo JSON")
                if engine.load_scenario(ruta_custom):
                    escenario_actual = ruta_custom
            else:
                try:
                    num = int(eleccion)
                    if 1 <= num <= len(escenarios):
                        ruta_sel = escenarios[num - 1]
                        if engine.load_scenario(ruta_sel):
                            escenario_actual = ruta_sel
                    else:
                        console.print("[red]Numero no valido.[/red]")
                except ValueError:
                    console.print("[red]Opcion no valida.[/red]")

        elif opcion == "2":
            if not escenario_actual:
                console.print("[yellow]Primero debes cargar un escenario (Opcion 1).[/yellow]")
                continue

            activar_banquero = Confirm.ask(
                "¿Deseas activar la Evasion con el Algoritmo del Banquero?",
                default=False
            )
            engine = SystemSimulatorEngine(use_banker=activar_banquero)
            engine.load_scenario(escenario_actual)

            engine.run_all(verbose=True)
            console.print()
            engine.metrics_collector.mostrar_tabla_metricas()

            if HAS_VISUALIZATION and Confirm.ask("\n¿Deseas visualizar el Grafo RAG resultante?", default=False):
                engine.show_rag_visualization()

        elif opcion == "3":
            if not escenario_actual:
                console.print("[yellow]Primero debes cargar un escenario (Opcion 1).[/yellow]")
                continue

            activar_banquero = Confirm.ask(
                "¿Deseas activar la Evasion con el Algoritmo del Banquero?",
                default=False
            )
            engine = SystemSimulatorEngine(use_banker=activar_banquero)
            engine.load_scenario(escenario_actual)

            step_num = 1
            while True:
                console.clear()
                console.rule(f"[bold cyan]Modo Paso a Paso - Tick #{step_num}[/bold cyan]", style="cyan")
                hay_progreso = engine.step(verbose=True)

                console.print()
                ui.mostrar_tabla_procesos(engine.processes)
                console.print()
                ui.mostrar_barra_memoria(engine.memory_manager)
                console.print()
                ui.mostrar_tabla_recursos(engine.resource_manager)

                if not hay_progreso:
                    console.print("\n[yellow]La simulacion se ha detenido (no hay mas acciones pendientes o interbloqueo total).[/yellow]")
                    break

                accion = Prompt.ask(
                    "\n[bold green][ENTER][/bold green] Siguiente paso | [bold red][Q][/bold red] Terminar | [bold cyan][G][/bold cyan] Grafo RAG",
                    default=""
                )
                if accion.upper() == "Q":
                    break
                elif accion.upper() == "G":
                    engine.show_rag_visualization()

                step_num += 1

            console.print("\n[bold]Resumen de metricas del recorrido:[/bold]")
            deadlock_info = {
                "detectados": engine.deadlock_history["detectados"],
                "resueltos": engine.banker_strategy.avoided_deadlocks_count if engine.use_banker else 0,
                "recursos": sorted(list(engine.deadlock_history["recursos"]))
            }
            engine.metrics_collector.recopilar(
                engine.processes, engine.memory_manager, engine.resource_manager, deadlock_info
            )
            engine.metrics_collector.mostrar_tabla_metricas()

        elif opcion == "4":
            if not engine.processes:
                console.print("[yellow]No hay procesos en ejecucion ni escenario cargado.[/yellow]")
            else:
                ui.mostrar_dashboard(
                    engine.processes,
                    engine.memory_manager,
                    engine.file_manager,
                    engine.resource_manager
                )

        elif opcion == "5":
            ui.mostrar_hardware()

        elif opcion == "6":
            console.print("\n[bold cyan]Saliendo del simulador de SO. ¡Hasta pronto![/bold cyan]\n")
            sys.exit(0)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Simulador de Micro-Kernel SO - Administracion de Recursos e Interbloqueos",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-s", "--scenario", type=str, help="Ruta al archivo de escenario JSON")
    parser.add_argument("-m", "--mode", choices=["auto", "step"], default="auto", help="Modo de ejecucion: 'auto' o 'step'")
    parser.add_argument("-b", "--banker", action="store_true", help="Habilita la evasion con Algoritmo del Banquero")
    parser.add_argument("-r", "--rag", action="store_true", help="Muestra la ventana grafica del Grafo RAG al finalizar")
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.scenario:
        engine = SystemSimulatorEngine(use_banker=args.banker)
        if not engine.load_scenario(args.scenario):
            sys.exit(1)

        if args.mode == "auto":
            engine.run_all(verbose=True)
            console.print()
            engine.metrics_collector.mostrar_tabla_metricas()
        elif args.mode == "step":
            while engine.step(verbose=True):
                ui.mostrar_tabla_procesos(engine.processes)
                input("\n[ENTER] para siguiente paso...")
            engine.metrics_collector.recopilar(
                engine.processes, engine.memory_manager, engine.resource_manager
            )
            engine.metrics_collector.mostrar_tabla_metricas()

        if args.rag:
            engine.show_rag_visualization()
    else:
        menu_interactivo()


if __name__ == "__main__":
    main()
