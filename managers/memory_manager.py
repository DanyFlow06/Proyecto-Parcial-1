class MemoryManager:
    def __init__(self, total_memory):
        # 4 variables internas estrictamente requeridas
        self.total_memory = total_memory
        self.used_memory = 0
        self.available_memory = total_memory
        self.peak_memory_used = 0

    def allocate_memory(self, process):
        # Revisa si hay suficiente memoria disponible
        if process.memory_required <= self.available_memory:
            self.available_memory -= process.memory_required
            self.used_memory += process.memory_required
            
            # Actualiza el récord histórico de uso máximo
            if self.used_memory > self.peak_memory_used:
                self.peak_memory_used = self.used_memory
                
            process.state = "ACTIVO_O_LISTO"
            return True
        else:
            # Rechaza la solicitud y notifica pasando a estado de espera
            process.state = "ESPERANDO"
            return False

    def release_memory(self, process):
        # Devuelve la memoria a la bolsa disponible
        self.available_memory += process.memory_required
        self.used_memory -= process.memory_required
