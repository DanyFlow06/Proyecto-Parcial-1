from typing import List, Dict, Any, Optional, Set, Tuple
import networkx as nx
from logger import log_info, log_warning
from process import Process, ESTADO_BLOQUEADO

class DeadlockDetector:
    """
    Detector algoritmico de interbloqueos y evaluador de las 4 Condiciones de Coffman.
    Utiliza NetworkX para construir el Grafo de Asignacion de Recursos (RAG) bipartito y dirigido.
    """
    def __init__(self):
        pass

    def build_rag(self, processes: List[Process], resource_manager) -> nx.DiGraph:
        """
        Construye el Grafo de Asignacion de Recursos (RAG) dirigido bipartito.
        - Nodos de Procesos: etiquetados con PID (node_type='process')
        - Nodos de Recursos: etiquetados con nombre (node_type='resource')
        - Aristas de Asignacion: Recurso -> Proceso (el recurso esta en poder del proceso)
        - Aristas de Solicitud: Proceso -> Recurso (el proceso espera en cola por el recurso)
        """
        rag = nx.DiGraph()

        # 1. Agregar nodos de procesos
        for p in processes:
            rag.add_node(
                p.pid,
                node_type="process",
                state=p.state,
                memory_required=p.memory_required
            )

        # 2. Agregar nodos de recursos
        for res_name, res_info in resource_manager.resources.items():
            rag.add_node(
                res_name,
                node_type="resource",
                res_type=res_info["type"],
                total_units=res_info["total_units"],
                available_units=res_info["available_units"]
            )

        # 3. Aristas de Asignacion: Recurso -> Proceso
        for res_name, alloc_map in resource_manager.allocations.items():
            for pid, units in alloc_map.items():
                if units > 0 and rag.has_node(pid):
                    rag.add_edge(res_name, pid, edge_type="assignment", units=units)

        # 4. Aristas de Solicitud / Espera: Proceso -> Recurso
        for res_name, queue in resource_manager.waiting_queue.items():
            for entry in queue:
                wait_p = entry["process"]
                req_units = entry["units"]
                if rag.has_node(wait_p.pid):
                    rag.add_edge(wait_p.pid, res_name, edge_type="request", units=req_units)

        return rag

    def check_coffman_conditions(
        self,
        processes: List[Process],
        resource_manager,
        rag: Optional[nx.DiGraph] = None
    ) -> Dict[str, Any]:
        """
        Evalua programaticamente las 4 Condiciones de Coffman mediante teoria de grafos:
        1. Exclusion Mutua: Al menos un recurso exclusivo asignado a un proceso.
        2. Retencion y Espera: Proceso con in_degree > 0 (retiene) y out_degree > 0 (espera).
        3. No Expropiacion: Recursos no expropiables en el sistema simulado.
        4. Espera Circular: Ciclo dirigido en el grafo RAG.
        """
        if rag is None:
            rag = self.build_rag(processes, resource_manager)

        # ── 1. Exclusion Mutua ────────────────────────────────────────────────
        exclusive_assigned = any(
            res_info["type"] == "exclusive" and len(resource_manager.allocations.get(res_name, {})) > 0
            for res_name, res_info in resource_manager.resources.items()
        )

        # ── 2. Retencion y Espera (Optimizacion Teoria de Grafos O(P)) ─────────
        # Un proceso retiene y espera si tiene simultaneamente aristas entrantes y salientes
        processes_holding_and_waiting = [
            p.pid for p in processes
            if rag.has_node(p.pid) and rag.in_degree(p.pid) > 0 and rag.out_degree(p.pid) > 0
        ]
        hold_and_wait = len(processes_holding_and_waiting) > 0

        # ── 3. No Expropiacion ────────────────────────────────────────────────
        # Los recursos en este sistema operativo simulado solo se liberan voluntariamente
        no_preemption = True

        # ── 4. Espera Circular (Búsqueda Optimizada con NetworkX O(V+E)) ───────
        cycles: List[List[str]] = []
        if not nx.is_directed_acyclic_graph(rag):
            cycles = list(nx.simple_cycles(rag))
        circular_wait = len(cycles) > 0

        deadlock_active = exclusive_assigned and hold_and_wait and no_preemption and circular_wait

        return {
            "mutua_exclusion": {
                "active": exclusive_assigned,
                "detail": (
                    "Existen recursos de uso exclusivo asignados a procesos."
                    if exclusive_assigned else "No hay contencion activa sobre recursos exclusivos."
                )
            },
            "retencion_y_espera": {
                "active": hold_and_wait,
                "processes": processes_holding_and_waiting,
                "detail": (
                    f"Procesos que retienen y esperan simultaneamente: {processes_holding_and_waiting}."
                    if hold_and_wait else "Ningun proceso retiene recursos mientras espera otros."
                )
            },
            "no_expropiacion": {
                "active": no_preemption,
                "detail": "No se permite la expropiacion forzosa de recursos asignados."
            },
            "espera_circular": {
                "active": circular_wait,
                "cycles_count": len(cycles),
                "detail": (
                    f"Se detectaron {len(cycles)} ciclo(s) dirigido(s) en el Grafo RAG."
                    if circular_wait else "No se detectaron ciclos en el Grafo RAG (Grafo aciclico)."
                )
            },
            "deadlock_present": deadlock_active,
            "cycles": cycles
        }

    def detect_deadlock(self, processes: List[Process], resource_manager) -> Dict[str, Any]:
        """
        Analisis exhaustivo de interbloqueos:
        Construye el RAG, evalua Coffman, identifica procesos y recursos atrapados,
        extrae aristas criticas para visualizacion y actualiza el estado a BLOQUEADO.
        """
        rag = self.build_rag(processes, resource_manager)
        coffman = self.check_coffman_conditions(processes, resource_manager, rag)

        cycles = coffman["cycles"]
        deadlocked_processes: Set[str] = set()
        deadlocked_resources: Set[str] = set()
        deadlock_edges: List[Tuple[str, str]] = []

        if coffman["deadlock_present"]:
            for cycle in cycles:
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    deadlock_edges.append((u, v))

                    # Clasificar nodo segun atributo en el RAG
                    node_type = rag.nodes[u].get("node_type")
                    if node_type == "process":
                        deadlocked_processes.add(u)
                    elif node_type == "resource":
                        deadlocked_resources.add(u)

            # Transicionar procesos en deadlock a estado BLOQUEADO oficial
            for p in processes:
                if p.pid in deadlocked_processes and p.state != ESTADO_BLOQUEADO:
                    p.change_state(ESTADO_BLOQUEADO)

            log_warning(
                f"INTERBLOQUEO DETECTADO: Procesos atrapados: {sorted(list(deadlocked_processes))} | "
                f"Recursos comprometidos: {sorted(list(deadlocked_resources))}."
            )
        else:
            log_info("DEADLOCK DETECTOR: Sistema en estado fluido sin interbloqueos.")

        return {
            "has_deadlock": coffman["deadlock_present"],
            "cycles": cycles,
            "deadlocked_pids": sorted(list(deadlocked_processes)),
            "deadlocked_resources": sorted(list(deadlocked_resources)),
            "deadlock_edges": deadlock_edges,
            "coffman_status": coffman,
            "graph": rag
        }
