from typing import List, Dict, Any, Tuple, Optional
from copy import deepcopy
from logger import log_info, log_warning
from process import Process, ESTADO_ESPERANDO

class BankerStrategy:
    """
    Estrategia de evasion dinamica de interbloqueos mediante el Algoritmo del Banquero (Dijkstra).
    Evalua el Estado de Seguridad del sistema antes de otorgar cualquier recurso.
    """
    def __init__(self):
        self.avoided_deadlocks_count: int = 0

    def compute_max_matrix(self, processes: List[Process], resource_manager) -> Dict[str, Dict[str, int]]:
        """
        Determina dinamicamente la demanda maxima de cada recurso por proceso
        a partir de sus instrucciones programadas y asignaciones actuales.
        """
        all_res = list(resource_manager.resources.keys())
        max_matrix: Dict[str, Dict[str, int]] = {}

        for p in processes:
            max_matrix[p.pid] = {r: 0 for r in all_res}

            # 1. Base: unidades actualmente asignadas
            for r in p.resources_held:
                if r in max_matrix[p.pid]:
                    units_held = resource_manager.allocations.get(r, {}).get(p.pid, 1)
                    max_matrix[p.pid][r] = max(max_matrix[p.pid][r], units_held)

            # 2. Sumar solicitudes futuras encontradas en pending_actions
            for action in p.pending_actions:
                if action.get("action") == "request_resource":
                    r_name = action.get("resource")
                    req_units = int(action.get("units", 1))
                    if r_name in max_matrix[p.pid]:
                        max_matrix[p.pid][r_name] += req_units

            # 3. Garantizar al menos 1 unidad si el proceso ya retiene el recurso
            for r in p.resources_held:
                if max_matrix[p.pid].get(r, 0) == 0:
                    max_matrix[p.pid][r] = 1

        return max_matrix

    def is_safe_state(
        self,
        available: Dict[str, int],
        allocation: Dict[str, Dict[str, int]],
        need: Dict[str, Dict[str, int]],
        pids: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Algoritmo de Seguridad del Banquero (Dijkstra).
        Determina si existe una secuencia segura de ejecucion donde todos los procesos
        puedan terminar sin entrar en inanicion o interbloqueo.

        Retorna:
            (is_safe, safe_sequence): Tupla booleana y la lista ordenada de PIDs seguros.
        """
        work = dict(available)
        finish = {pid: False for pid in pids}
        safe_sequence: List[str] = []
        all_res = list(available.keys())

        while len(safe_sequence) < len(pids):
            found_candidate = False

            for pid in pids:
                if not finish[pid]:
                    # Condicion de suficiencia: Need[pid][R] <= Work[R] para todo recurso
                    can_satisfy = all(need[pid].get(r, 0) <= work.get(r, 0) for r in all_res)

                    if can_satisfy:
                        # Se asume que el proceso concluye y devuelve todos sus recursos asignados
                        for r in all_res:
                            work[r] = work.get(r, 0) + allocation.get(r, {}).get(pid, 0)

                        finish[pid] = True
                        safe_sequence.append(pid)
                        found_candidate = True
                        break

            # Si en una pasada completa ningun proceso pudo satisfacerse, el estado es INSEGURO
            if not found_candidate:
                return False, []

        return True, safe_sequence

    def evaluate_request(
        self,
        process: Process,
        resource_name: str,
        requested_units: int,
        processes: List[Process],
        resource_manager
    ) -> Tuple[bool, str, List[str]]:
        """
        Simula provisionalmente la asignacion y comprueba si el estado resultante es seguro.
        No muta el estado real del ResourceManager.
        """
        if resource_name not in resource_manager.resources:
            return False, f"Recurso '{resource_name}' no existe en el sistema.", []

        res_info = resource_manager.resources[resource_name]
        is_exclusive = res_info["type"] == "exclusive"
        req_units = 1 if is_exclusive else max(1, requested_units)

        # 1. Comprobar si hay unidades disponibles fisicas
        if req_units > res_info["available_units"]:
            return False, f"Unidades insuficientes de '{resource_name}' ({req_units} pedidas, {res_info['available_units']} libres).", []

        # 2. Filtrar solo procesos activos (no terminados)
        active_processes = [p for p in processes if not p.is_finished()]
        active_pids = [p.pid for p in active_processes]

        if process.pid not in active_pids:
            active_pids.append(process.pid)

        # 3. Construir matrices Max, Alloc y Need
        max_matrix = self.compute_max_matrix(active_processes, resource_manager)

        alloc_matrix = {
            r: {pid: resource_manager.allocations.get(r, {}).get(pid, 0) for pid in active_pids}
            for r in resource_manager.resources.keys()
        }

        need_matrix = {}
        for pid in active_pids:
            need_matrix[pid] = {}
            for r in resource_manager.resources.keys():
                max_u = max_matrix.get(pid, {}).get(r, 0)
                alloc_u = alloc_matrix[r].get(pid, 0)
                need_matrix[pid][r] = max(0, max_u - alloc_u)

        # 4. Simular asignacion provisional (Pretend Allocation)
        sim_avail = {r: resource_manager.resources[r]["available_units"] for r in resource_manager.resources.keys()}
        sim_avail[resource_name] -= req_units
        alloc_matrix[resource_name][process.pid] = alloc_matrix[resource_name].get(process.pid, 0) + req_units
        need_matrix[process.pid][resource_name] = max(0, need_matrix[process.pid].get(resource_name, 0) - req_units)

        # 5. Ejecutar Algoritmo de Seguridad
        is_safe, safe_seq = self.is_safe_state(sim_avail, alloc_matrix, need_matrix, active_pids)

        if is_safe:
            return True, "Estado Seguro verificado.", safe_seq
        else:
            return False, "Estado Inseguro detectado: otorgar este recurso provocaria un deadlock.", []

    def request_resource_safe(
        self,
        resource_name: str,
        process: Process,
        processes: List[Process],
        resource_manager,
        units: int = 1
    ) -> bool:
        """
        Punto de entrada de alta cohesion:
        Evalua la peticion. Si es segura, la otorga inmediatamente con el ResourceManager.
        Si es insegura, frena la peticion, transiciona al proceso a ESPERANDO y previene el deadlock.
        """
        is_safe, msg, safe_seq = self.evaluate_request(
            process=process,
            resource_name=resource_name,
            requested_units=units,
            processes=processes,
            resource_manager=resource_manager
        )

        if is_safe:
            resource_manager.request_resource(resource_name, process, units)
            log_info(
                f"BANQUERO (APROBADO): Peticion de PID={process.pid} sobre '{resource_name}' ({units}u) CONCEDIDA. "
                f"Secuencia segura garantizada: {safe_seq}."
            )
            return True
        else:
            self.avoided_deadlocks_count += 1
            process.change_state(ESTADO_ESPERANDO)
            log_warning(
                f"BANQUERO (EVASION EXITOSA): Peticion de PID={process.pid} sobre '{resource_name}' DENEGADA. "
                f"Motivo: {msg}. Proceso pasa a ESPERANDO para evitar interbloqueo."
            )
            return False
