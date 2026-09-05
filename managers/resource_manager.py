from typing import List, Dict, Any, Optional
from logger import log_info, log_warning, log_error
from process import ESTADO_ACTIVO_O_LISTO, ESTADO_ESPERANDO

class ResourceManager:
    """
    Administrador de recursos exclusivos (uso uniproceso) y compartidos (multiples unidades).
    Gestiona solicitudes, liberaciones y colas de espera con politica FIFO.
    """
    def __init__(self, resources_data: List[Dict[str, Any]]):
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.allocations: Dict[str, Dict[str, int]] = {}
        self.waiting_queue: Dict[str, List[Dict[str, Any]]] = {}

        # Metricas para la auditoria y resumen final
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.wait_transitions: int = 0
        self.total_releases: int = 0

        self._load_resources(resources_data)
        log_info(f"ResourceManager inicializado con {len(self.resources)} recursos.")

    def _load_resources(self, resources_data: List[Dict[str, Any]]) -> None:
        """Carga el catalogo de recursos desde la estructura del escenario JSON."""
        for item in resources_data:
            name = item["name"]
            res_type = item.get("type", "exclusive")
            units = int(item.get("units", 1)) if res_type == "shared" else 1

            self.resources[name] = {
                "name": name,
                "type": res_type,
                "total_units": units,
                "available_units": units
            }
            self.allocations[name] = {}
            self.waiting_queue[name] = []

    # ── Compatibilidad con cli_interface.py de Daniel ─────────────────────────
    @property
    def allocation(self) -> Dict[str, Any]:
        """
        Retorna la asignacion actual formateada para la vista CLI:
        Mapea resource_name -> PID asignado (o string con lista de PIDs si es compartido).
        """
        result = {}
        for res_name, alloc_map in self.allocations.items():
            if not alloc_map:
                result[res_name] = None
            elif len(alloc_map) == 1:
                pid, units = next(iter(alloc_map.items()))
                result[res_name] = f"PID={pid}" if self.resources[res_name]["type"] == "exclusive" else f"PID={pid} ({units}u)"
            else:
                result[res_name] = ", ".join(f"PID={pid} ({u}u)" for pid, u in alloc_map.items())
        return result

    @property
    def waiting_queues(self) -> Dict[str, List[str]]:
        """
        Retorna las colas de espera formateadas para la vista CLI:
        Mapea resource_name -> lista de PIDs esperando.
        """
        return {
            res_name: [f"PID={entry['process'].pid}" for entry in queue]
            for res_name, queue in self.waiting_queue.items()
        }

    # ── Solicitud de recursos ──────────────────────────────────────────────────
    def request_resource(self, resource_name: str, process, units: int = 1) -> bool:
        """
        Solicita unidades de un recurso para un proceso.
        - Si hay disponibilidad y no hay procesos previos esperando en cola, se asigna inmediatamente.
        - Si no hay disponibilidad suficiente, el proceso pasa a ESPERANDO y se encola (FIFO).
        """
        self.total_requests += 1

        if resource_name not in self.resources:
            msg = f"PID={process.pid}: Error al solicitar recurso inexistente '{resource_name}'."
            log_error(msg)
            return False

        res_info = self.resources[resource_name]
        is_exclusive = res_info["type"] == "exclusive"
        requested_units = 1 if is_exclusive else max(1, units)

        # Regla FIFO: Solo otorgar de inmediato si hay suficientes unidades Y la cola de espera esta vacia
        can_grant = (res_info["available_units"] >= requested_units) and (len(self.waiting_queue[resource_name]) == 0)

        if can_grant:
            # Asignacion directa
            res_info["available_units"] -= requested_units
            self.allocations[resource_name][process.pid] = (
                self.allocations[resource_name].get(process.pid, 0) + requested_units
            )

            process.add_resource(resource_name)
            process.change_state(ESTADO_ACTIVO_O_LISTO)

            self.successful_requests += 1
            log_info(
                f"PID={process.pid}: Recurso '{resource_name}' asignado ({requested_units} unid.). "
                f"Disponibles restantes: {res_info['available_units']}."
            )
            return True
        else:
            # Poner en espera y encolar
            self.wait_transitions += 1
            process.change_state(ESTADO_ESPERANDO)

            # Evitar duplicados en cola para el mismo proceso
            already_waiting = any(entry["process"].pid == process.pid for entry in self.waiting_queue[resource_name])
            if not already_waiting:
                self.waiting_queue[resource_name].append({
                    "process": process,
                    "units": requested_units
                })

            log_warning(
                f"PID={process.pid}: Recurso '{resource_name}' no disponible "
                f"(Solicito: {requested_units}, Libres: {res_info['available_units']}). "
                f"Proceso pasa a ESPERANDO (Posicion en cola: {len(self.waiting_queue[resource_name])})."
            )
            return False

    # ── Liberacion de recursos ────────────────────────────────────────────────
    def release_resource(self, resource_name: str, process, units: int = 1) -> bool:
        """
        Libera unidades de un recurso retenido por el proceso.
        Al liberar, despierta (wake-up) de forma automatica a los procesos en espera bajo politica FIFO.
        """
        self.total_releases += 1

        if resource_name not in self.resources:
            log_error(f"PID={process.pid}: Error al liberar recurso inexistente '{resource_name}'.")
            return False

        current_held = self.allocations[resource_name].get(process.pid, 0)
        if current_held <= 0:
            log_warning(f"PID={process.pid}: Intento de liberar '{resource_name}' que no tiene asignado.")
            return False

        res_info = self.resources[resource_name]
        units_to_release = min(current_held, units)

        # Desasignar unidades
        self.allocations[resource_name][process.pid] -= units_to_release
        if self.allocations[resource_name][process.pid] == 0:
            del self.allocations[resource_name][process.pid]
            process.release_resource(resource_name)

        res_info["available_units"] += units_to_release
        log_info(
            f"PID={process.pid}: Libero {units_to_release} unid. de '{resource_name}'. "
            f"Disponibles ahora: {res_info['available_units']}."
        )

        # Despertar procesos en espera (Wake-up FIFO)
        self._wake_up_waiting(resource_name)
        return True

    def _wake_up_waiting(self, resource_name: str) -> None:
        """
        Examina la cola de espera FIFO del recurso y despacha a los procesos
        conforme las unidades disponibles alcancen.
        """
        res_info = self.resources[resource_name]
        queue = self.waiting_queue[resource_name]

        while queue and res_info["available_units"] >= queue[0]["units"]:
            next_entry = queue.pop(0)
            waiting_process = next_entry["process"]
            req_units = next_entry["units"]

            res_info["available_units"] -= req_units
            self.allocations[resource_name][waiting_process.pid] = (
                self.allocations[resource_name].get(waiting_process.pid, 0) + req_units
            )

            waiting_process.add_resource(resource_name)
            waiting_process.change_state(ESTADO_ACTIVO_O_LISTO)
            log_info(
                f"DESPERTAR (FIFO): Recurso '{resource_name}' asignado a PID={waiting_process.pid} "
                f"({req_units} unid.). Proceso reactivado a ACTIVO_O_LISTO."
            )

    # ── Consulta de estado y telemetria ───────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        """
        Devuelve una radiografia completa del estado de todos los recursos,
        asignaciones, colas y metricas acumuladas.
        """
        return {
            "resources": {
                name: {
                    "type": r["type"],
                    "total_units": r["total_units"],
                    "available_units": r["available_units"],
                    "allocations": dict(self.allocations.get(name, {})),
                    "waiting_count": len(self.waiting_queue.get(name, []))
                }
                for name, r in self.resources.items()
            },
            "metrics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "wait_transitions": self.wait_transitions,
                "total_releases": self.total_releases
            }
        }
