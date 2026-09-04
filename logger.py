import logging
import os

# Ruta para guardar los logs dentro de la carpeta logs/
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "simulacion.log")

# Creación automática del directorio de logs si no existe
os.makedirs(LOG_DIR, exist_ok=True)

# Instancia global del logger
logger = logging.getLogger("SimuladorSO")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # Formato con fecha y hora exacta
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Handler para el archivo logs/simulacion.log
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler para la consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def log_info(msg: str) -> None:
    """Registra un mensaje de nivel INFO."""
    logger.info(msg)

def log_warning(msg: str) -> None:
    """Registra un mensaje de nivel WARNING."""
    logger.warning(msg)

def log_error(msg: str) -> None:
    """Registra un mensaje de nivel ERROR."""
    logger.error(msg)
