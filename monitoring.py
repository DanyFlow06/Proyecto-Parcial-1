import psutil

def get_hardware_status():
    # Porcentaje de CPU (pequeño intervalo para lectura real)
    cpu_percent = psutil.cpu_percent(interval=0.5)
    
    # RAM física
    ram_info = psutil.virtual_memory()
    
    # Disco (espacio disponible en raíz)
    disk_info = psutil.disk_usage('/')
    
    # Red (actividad básica)
    net_info = psutil.net_io_counters()
    
    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram_info.percent,
        "disk_free_gb": round(disk_info.free / (1024 ** 3), 2),
        "network_bytes_sent": net_info.bytes_sent,
        "network_bytes_recv": net_info.bytes_recv
    }
