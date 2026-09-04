from typing import List, Dict, Any, Optional
from logger import logger

# Constantes oficiales para los 4 estados permitidos
ESTADO_ACTIVO_O_LISTO = "ACTIVO_O_LISTO"
ESTADO_ESPERANDO = "ESPERANDO"
ESTADO_BLOQUEADO = "BLOQUEADO"
ESTADO_TERMINADO = "TERMINADO"

ESTADOS_VALIDOS = {
    ESTADO_ACTIVO_O_LISTO,
    ESTADO_ESPERANDO,
    ESTADO_BLOQUEADO,
    ESTADO_TERMINADO
}

class Process:
    """
    Representa a cada tarea o proceso dentro del simulador del Sistema Operativo.
    Cumple con los atributos obligatorios especificados en el Plan de Trabajo.
    """
    def __init__(
        self,
        pid: str,
        memory_required: int,
        resources_needed: Optional[List[str]] = None,
        instructions: Optional[List[Dict[str, Any]]] = None
    ):
        self.pid: str = str(pid)
        self.memory_required: int = int(memory_required)
        self.resources_needed: List[str] = resources_needed if resources_needed is not None else []
        self.resources_held: List[str] = []
        self.state: str = ESTADO_ACTIVO_O_LISTO
        self.pending_actions: List[Dict[str, Any]] = instructions if instructions is not None else []

        logger.info(f"Proceso '{self.pid}' inicializado. RAM requerida: {self.memory_required} MB.")

    def change_state(self, new_state: str) -> None:
        """
        Cambia el estado del proceso validando que sea uno de los 4 estados permitidos.
        """
        if new_state not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado '{new_state}' inválido. Debe ser uno de: {ESTADOS_VALIDOS}")
        
        old_state = self.state
        self.state = new_state
        logger.info(f"Proceso '{self.pid}': Transición de estado {old_state} -> {new_state}")

    def add_resource(self, resource_name: str) -> None:
        """
        Asigna un recurso al proceso y lo registra en la lista resources_held.
        """
        if resource_name not in self.resources_held:
            self.resources_held.append(resource_name)
            logger.info(f"Proceso '{self.pid}' asignó recurso '{resource_name}'.")

    def release_resource(self, resource_name: str) -> None:
        """
        Libera un recurso devuelto de la lista resources_held.
        """
        if resource_name in self.resources_held:
            self.resources_held.remove(resource_name)
            logger.info(f"Proceso '{self.pid}' liberó recurso '{resource_name}'.")

    def pop_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene y elimina la siguiente instrucción de la cola pending_actions.
        """
        if self.pending_actions:
            return self.pending_actions.pop(0)
        return None

    def peek_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Consulta la siguiente instrucción sin eliminarla.
        """
        if self.pending_actions:
            return self.pending_actions[0]
        return None

    def is_finished(self) -> bool:
        """Indica si el proceso ha alcanzado el estado TERMINADO."""
        return self.state == ESTADO_TERMINADO

    def __repr__(self) -> str:
        return (
            f"<Process pid='{self.pid}' state='{self.state}' "
            f"memory_required={self.memory_required} MB resources_held={self.resources_held}>"
        )