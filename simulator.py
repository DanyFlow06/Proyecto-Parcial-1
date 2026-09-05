import json
import sys

# Intentamos importar las clases de los compañeros (Sprint 1 y 2)
try:
    from managers.memory_manager import MemoryManager
    from managers.resource_manager import ResourceManager
    from managers.file_manager import FileManager
    from process import Process
except ImportError:
    # Variables de soporte por si aún no hacen merge a main
    MemoryManager = None
    ResourceManager = None
    FileManager = None
    Process = None

class Simulator:
    def __init__(self):
        self.memory_manager = None
        self.resource_manager = None
        self.file_manager = None
        self.processes = []
        self.metrics = {
            "procesos_totales": 0,
            "terminados": 0,
            "bloqueados": 0
        }

    def load_scenario(self, filepath):
        try:
            with open(filepath, 'r') as file:
                data = json.load(file)
                
            # Validar campos obligatorios (Tarea 2.3)
            required_fields = ["total_memory", "resources", "processes"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Falta el campo obligatorio: '{field}'")
            
            # Instanciar administradores si los módulos ya existen
            if MemoryManager:
                self.memory_manager = MemoryManager(data["total_memory"])
            if ResourceManager:
                self.resource_manager = ResourceManager(data["resources"])
            if FileManager:
                self.file_manager = FileManager()

            # Instanciar procesos
            self.processes = []
            if Process:
                for p_data in data["processes"]:
                    process = Process(
                        pid=p_data["pid"],
                        memory_required=p_data["memory_required"],
                        instructions=p_data["instructions"]
                    )
                    self.processes.append(process)
                    self.metrics["procesos_totales"] += 1
            else:
                # Si falta la clase Process temporalmente, almacenamos los datos crudos
                self.processes = data["processes"]
                self.metrics["procesos_totales"] = len(self.processes)
                
            print(f"✅ Escenario '{filepath}' cargado exitosamente.")
            return True
            
        except FileNotFoundError:
            print(f"❌ Error: No se encontró el archivo '{filepath}'.")
            return False
        except json.JSONDecodeError:
            print(f"❌ Error: El archivo '{filepath}' no tiene un formato JSON válido.")
            return False
        except ValueError as ve:
            print(f"❌ Error de validación: {ve}")
            return False
        except Exception as e:
            print(f"❌ Error inesperado al cargar el escenario: {e}")
            return False

    def step(self):
        # Tarea 2.4 - Modo Paso a Paso
        # Procesa una sola instrucción, pausa el sistema y espera al usuario.
        for process in self.processes:
            state = process.state if hasattr(process, 'state') else process.get("state", "ACTIVO_O_LISTO")
            pending = process.instructions if hasattr(process, 'instructions') else process.get("instructions", [])
            pid = process.pid if hasattr(process, 'pid') else process.get("pid")
            
            if state == "ACTIVO_O_LISTO" and pending:
                action = pending.pop(0)
                action_type = action.get("action")
                resource = action.get("resource") or action.get("file")
                
                print(f"▶️ [Paso] Proceso {pid} ejecutando: {action_type} sobre {resource}")
                
                if action_type == "request_resource" and self.resource_manager:
                    self.resource_manager.request_resource(resource, process)
                elif action_type == "release_resource" and self.resource_manager:
                    self.resource_manager.release_resource(resource, process)
                
                # Actualizar estado si el proceso ya no tiene más instrucciones
                if not pending:
                    if hasattr(process, 'state'):
                        process.state = "TERMINADO"
                    else:
                        process["state"] = "TERMINADO"
                    self.metrics["terminados"] += 1

                input("\nPresiona ENTER para inspeccionar el estado y continuar...")
                return True
                
        return False

    def run_automatic_mode(self):
        # Tarea 2.4 - Modo Automático
        # Avanza sin parar hasta que se terminen los procesos o se bloqueen.
        print("\n🚀 Iniciando Modo Automático...")
        while True:
            made_progress = False
            for process in self.processes:
                state = process.state if hasattr(process, 'state') else process.get("state", "ACTIVO_O_LISTO")
                pending = process.instructions if hasattr(process, 'instructions') else process.get("instructions", [])
                
                if state == "ACTIVO_O_LISTO" and pending:
                    action = pending.pop(0)
                    action_type = action.get("action")
                    pid = process.pid if hasattr(process, 'pid') else process.get("pid")
                    resource = action.get("resource") or action.get("file")
                    
                    print(f"  -> {pid} : {action_type} ({resource})")
                    made_progress = True
                    
                    if action_type == "request_resource" and self.resource_manager:
                        self.resource_manager.request_resource(resource, process)
                    elif action_type == "release_resource" and self.resource_manager:
                        self.resource_manager.release_resource(resource, process)
                    
                    if not pending:
                        if hasattr(process, 'state'):
                            process.state = "TERMINADO"
                        else:
                            process["state"] = "TERMINADO"
                        self.metrics["terminados"] += 1

            # Termina el ciclo si nadie avanzó (todos terminaron o quedaron congelados)
            if not made_progress:
                break
        
        # Conteo final de procesos bloqueados
        for process in self.processes:
            state = process.state if hasattr(process, 'state') else process.get("state", "ACTIVO_O_LISTO")
            if state in ["ESPERANDO", "BLOQUEADO"]:
                self.metrics["bloqueados"] += 1

        self.print_summary()

    def print_summary(self):
        print("\n📊 --- Resumen Final de Métricas ---")
        print(f"Procesos Totales: {self.metrics['procesos_totales']}")
        print(f"Procesos Terminados: {self.metrics['terminados']}")
        print(f"Procesos Bloqueados: {self.metrics['bloqueados']}")
        print("------------------------------------\n")
