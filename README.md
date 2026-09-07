# 🖥️ Simulador de Micro-Kernel SO: Administración de Recursos e Interbloqueos

> **Asignatura:** Sistemas Operativos — 5to Semestre  
> **Institución:** Universidad Autónoma de Querétaro (UAQ)  
> **Proyecto:** Simulador Discreto de Micro-Kernel para la Gestión Concurrente de Recursos, Detección de Deadlocks y Evasión con el Algoritmo del Banquero  
> **Equipo de Desarrollo:**  
> - **Uriel** *(Líder del Proyecto & Revisor de PR)*: `process.py`, `logger.py`, `managers/resource_manager.py`, `deadlock_detector.py`, `banker_strategy.py`.  
> - **Chris**: `managers/memory_manager.py`, `monitoring.py`, `simulator.py`, `visualization.py`.  
> - **Daniel**: `managers/file_manager.py`, `cli_interface.py`, `scenarios/` (1 al 5), `metrics.py`, `main.py`, pruebas de blindaje y `README.md`.

---

## 📌 1. Descripción General del Proyecto

Este software es un **simulador de eventos discretos que modela el núcleo (kernel) de un Sistema Operativo multiprogramado**. Su objetivo primordial es recrear con rigor teórico la competencia concurrente entre múltiples procesos por recursos finitos del sistema (memoria RAM simulada, dispositivos de E/S exclusivos o compartidos, y archivos virtuales en memoria), gestionando de manera matemática y visual los estados de contención e **interbloqueos (*deadlocks*)**.

### Capacidades Principales:
1. **Gestión Modular de Recursos (`managers/`):** Control estricto de memoria RAM con registro de pico histórico, inventario de dispositivos exclusivos y compartidos con encolamiento FIFO, y sistema de archivos virtuales con control de concurrencia mediante cerrojos (*locks*).
2. **Ciclo de Vida Formal de Procesos:** Modelado estricto de los 4 estados canónicos de los procesos: `ACTIVO_O_LISTO`, `ESPERANDO`, `BLOQUEADO` y `TERMINADO`.
3. **Detección Automática de Deadlocks (Teoría de Grafos):** Verificación programática de las **4 Condiciones de Coffman** y extracción de ciclos dirigidos en el **Grafo de Asignación de Recursos (RAG)** mediante `networkx`.
4. **Evasión Activa con Algoritmo del Banquero:** Implementación del algoritmo de Dijkstra para evaluar estados seguros antes de conceder cualquier recurso, encolando temporalmente solicitudes riesgosas para evitar el colapso del sistema.
5. **Visualización Gráfica y Dashboard Rich:** Interfaz enriquecida de terminal con tablas tabulares, barras de RAM y métricas en vivo (`rich`), además de ventanas emergentes con el grafo RAG resaltando ciclos críticos en color rojo (`matplotlib`).
6. **Auditoría Exhaustiva de 9 Métricas:** Reporte final completo al término de la simulación que garantiza la liberación limpia y ausencia de fugas de recursos.
7. **100% Dinámico (Blindaje contra Escenario Sorpresa):** El motor no asume identificadores estáticos (`"P1"`, `"Impresora_1"`); soporta cualquier denominación o estructura de procesos arbitraria.

---

## 🏗️ 2. Arquitectura del Sistema

El simulador sigue el modelo canónico de **4 capas de abstracción de un Sistema Operativo**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. CAPA APLICACIÓN: Escenarios JSON / Instrucciones de Procesos        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. CAPA SHELL / CLI: main.py & cli_interface.py (Menú y Rich Dashboard)│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. CAPA KERNEL SIMULADO:                                               │
│    • process.py (Ciclo de Vida)   • memory_manager.py (RAM)            │
│    • resource_manager.py (FIFO)   • file_manager.py (CRUD & Locks)      │
│    • deadlock_detector.py (Grafo) • banker_strategy.py (Evasión)       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. CAPA HARDWARE:                                                      │
│    • Hardware Simulado: RAM Virtual, Dispositivos e Inodos Virtuales   │
│    • Hardware Real: psutil (CPU %, RAM física, Disco y Red anfitrión)  │
└────────────────────────────────────────────────────────────────────────┘
```

### Mapeo con 5 Llamadas al Sistema Reales (Syscalls POSIX)

| Operación Simulada | Syscall POSIX / Linux | Justificación Técnica en Sistemas Operativos |
| :--- | :--- | :--- |
| **Solicitud de RAM** | `brk()` / `mmap()` | Modifica el límite del segmento de datos (*heap*) o crea un mapeo de páginas anónimas en el espacio de direcciones virtual. |
| **Creación de Archivo** | `creat()` / `open(..., O_CREAT)` | Reserva una entrada de directorio y asigna un nuevo inodo en la tabla de inodos del sistema de archivos. |
| **Lectura / Escritura** | `read()` / `write()` | Transfiere bloques de bytes entre búferes del espacio de usuario y el caché de páginas gestionado por el kernel. |
| **Eliminación de Archivo** | `unlink()` | Decrementa el contador de enlaces duros del inodo; cuando llega a 0, el kernel libera los bloques de disco asociados. |
| **Petición de Recurso Exclusivo** | `sem_wait()` / `pthread_mutex_lock()` | Primitiva de sincronización atómica que evalúa el contador del semáforo/mutex y duerme al hilo/proceso en una cola de espera si el recurso está retenido. |

---

## 📁 3. Estructura del Repositorio

```text
Proyecto-Parcial-1/
├── main.py                     # Punto de entrada oficial, CLI interactivo y despachador
├── process.py                  # Definición de la clase Process y sus 4 estados canónicos
├── deadlock_detector.py        # Evaluación de Condiciones de Coffman y detección de ciclos RAG
├── banker_strategy.py          # Algoritmo del Banquero (Matrices Max, Need, Safe State)
├── simulator.py                # Motor de ejecución (Modo Automático y Paso a Paso)
├── cli_interface.py            # Vistas enriquecidas de terminal con tablas y paneles (Rich)
├── monitoring.py               # Monitoreo de telemetría del hardware real con psutil
├── visualization.py            # Despliegue de Grafo RAG con Matplotlib y NetworkX
├── metrics.py                  # Recopilador y renderizador de la tabla final de 9 métricas
├── test_stress_surprise.py     # Suite de blindaje y pruebas de estrés para Escenario Sorpresa
├── requirements.txt            # Dependencias del proyecto (rich, networkx, matplotlib, psutil)
├── README.md                   # Manual técnico y guía de usuario
│
├── managers/                   # Paquete de gestores del Kernel
│   ├── __init__.py             # Identificador de paquete Python
│   ├── memory_manager.py       # Administrador de memoria RAM simulada y pico histórico
│   ├── file_manager.py         # Sistema de archivos virtual con CRUD y exclusión mutua
│   └── resource_manager.py     # Administrador de recursos exclusivos y compartidos con FIFO
│
├── scenarios/                  # Banco de escenarios JSON de evaluación
│   ├── escenario_1.json        # Ejecución normal sin contención
│   ├── escenario_2.json        # Espera temporal que se resuelve sola (sin deadlock)
│   ├── escenario_3.json        # Interbloqueo real provocado (Espera circular pura)
│   ├── escenario_4.json        # Evasión exitosa con Algoritmo del Banquero
│   ├── escenario_5.json        # Escenario a gran escala (alta concurrencia)
│   └── escenario_sorpresa.json # Escenario de blindaje con identificadores heterogéneos
│
├── docs/                       # Documentación técnica de diseño y guías de defensa
│   ├── Plan de Trabajo y Guía del Proyecto SO.md
│   ├── Resumen Tecnico.md
│   └── Guia de Defensa Oral SO.md
│
└── logs/
    └── simulacion.log          # Registro histórico cronológico persistente
```

---

## ⚙️ 4. Requisitos e Instalación

### Requisitos Previos
* **Python 3.10** o superior instalado en el sistema.
* Administrador de paquetes `pip`.

### Instalación Paso a Paso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/DanyFlow06/Proyecto-Parcial-1.git
   cd Proyecto-Parcial-1
   ```

2. **Crear y activar un entorno virtual (Recomendado):**
   * En **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * En **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias oficiales:**
   ```bash
   pip install -r requirements.txt
   ```

Las dependencias instaladas son:
- `rich>=13.0.0`: Interfaz visual en consola (tablas, paneles, colores y barras).
- `networkx>=3.0`: Estructuras de datos para grafos dirigidos bipartitos y detección de ciclos.
- `matplotlib>=3.7.0`: Renderizado interactivo del Grafo de Asignación de Recursos (RAG).
- `psutil>=5.9.0`: Extracción de métricas en tiempo real del hardware del anfitrión.

---

## 🚀 5. Guía de Uso y Modos de Ejecución

El simulador ofrece dos formas de uso: **Menú Interactivo en Consola** o **Comandos Directos por Terminal (CLI)**.

### Opción A: Menú Interactivo Rich (Recomendado)

Ejecuta el archivo principal sin argumentos:
```bash
python main.py
```

Se desplegará el panel interactivo con las siguientes opciones:
1. **`1. Cargar escenario JSON`:** Permite elegir entre los 5 escenarios incluidos o introducir la ruta a un archivo JSON externo (*Escenario Sorpresa*).
2. **`2. Ejecutar en Modo Automático`:** Corre todo el lote de instrucciones de una sola vez y pregunta si se desea activar el **Algoritmo del Banquero**. Al finalizar, despliega la tabla de 9 métricas y ofrece abrir el Grafo RAG.
3. **`3. Ejecutar en Modo Paso a Paso`:** Avanza instrucción por instrucción (`tick`), permitiendo al usuario presionar `[ENTER]` para ver cómo cambia la tabla de procesos, el uso de RAM y la posesión de recursos, o presionar `[G]` para ver el grafo en vivo.
4. **`4. Ver estado del sistema (Dashboard)`:** Muestra el panel completo unificado del estado actual.
5. **`5. Ver hardware real`:** Despliega el uso actual de CPU, RAM física, disco y red con `psutil`.
6. **`6. Salir`:** Finaliza la sesión.

---

### Opción B: Comandos Directos por Terminal (CLI)

Puedes automatizar pruebas o demostraciones rápidas usando los parámetros de línea de comandos:

```bash
# Ver ayuda y parámetros disponibles
python main.py --help

# Ejecutar Escenario 1 en Modo Automático
python main.py --scenario scenarios/escenario_1.json --mode auto

# Ejecutar Escenario 3 (Deadlock provocado) y abrir el Grafo RAG al terminar
python main.py --scenario scenarios/escenario_3.json --mode auto --rag

# Ejecutar Escenario 4 activando la Evasión con el Algoritmo del Banquero
python main.py --scenario scenarios/escenario_4.json --mode auto --banker

# Ejecutar Escenario 2 en Modo Paso a Paso
python main.py --scenario scenarios/escenario_2.json --mode step
```

---

## 📊 6. Catálogo Oficial de Escenarios de Prueba

| Escenario | Nombre del Archivo | Objetivo Pedagógico y Comportamiento | Resultado Esperado |
| :---: | :--- | :--- | :--- |
| **1** | `escenario_1.json` | **Ejecución normal sin contención:** 3 procesos con recursos independientes y memoria suficiente. Operaciones de archivos limpias. | 100% procesos terminados exitosamente. 0 interbloqueos. |
| **2** | `escenario_2.json` | **Espera temporal (Sin deadlock):** Dos procesos compiten por un mismo recurso exclusivo (`Impresora_1`). Uno espera en cola FIFO hasta que el otro lo libera. | Transición correcta a `ESPERANDO`. El sistema despierta al proceso y concluye al 100% sin falsos positivos de deadlock. |
| **3** | `escenario_3.json` | **Interbloqueo puro (Espera circular):** Dos procesos (`Proceso_Alpha` y `Proceso_Beta`) toman un recurso y solicitan el que retiene el otro. | Cumplimiento de las 4 condiciones de Coffman. Detección del ciclo en el RAG y coloreado de aristas en **rojo**. |
| **4** | `escenario_4.json` | **Evasión con Algoritmo del Banquero:** Peticiones que conducirían a un estado inseguro son denegadas temporalmente por el banquero. | Sin banquero colapsa en deadlock; con banquero concluye con éxito resolviendo el interbloqueo preventivamente. |
| **5** | `escenario_5.json` | **Escenario a gran escala:** 6 procesos concurrentes compitiendo por 4 recursos (exclusivos y compartidos con unidades múltiples) y memoria. | Demuestra escalabilidad, estabilidad y gestión de concurrencia avanzada. |
| **Sorpresa** | `escenario_sorpresa.json` | **Blindaje contra datos no vistos:** Procesos y recursos con nombres no convencionales, operaciones CRUD complejas y límites de RAM. | Demuestra que el código es 100% dinámico y no posee identificadores fijos (*hardcoded*). |

---

## 🛡️ 7. Tratamiento Formal de Interbloqueos (*Deadlocks*)

### 1. Las 4 Condiciones de Coffman

Para que ocurra un interbloqueo deben cumplirse **simultáneamente** las cuatro condiciones:
1. **Exclusión Mutua (*Mutual Exclusion*):** Al menos un recurso se encuentra asignado a un único proceso y no puede ser compartido.
2. **Retención y Espera (*Hold and Wait*):** Un proceso retiene al menos un recurso mientras solicita recursos adicionales asignados a otros procesos.
3. **No Expropiación (*No Preemption*):** Los recursos no pueden ser arrebatados a la fuerza; solo se liberan voluntariamente por el proceso poseedor.
4. **Espera Circular (*Circular Wait*):** Existe una cadena cerrada de procesos $\{P_0, P_1, \dots, P_n\}$ donde cada $P_i$ espera un recurso retenido por $P_{(i+1) \pmod n}$.

El módulo `deadlock_detector.py` evalúa programáticamente cada condición en cada tick del micro-kernel.

### 2. Algoritmo del Banquero (Evasión de Dijkstra)

A diferencia de la detección a posteriori, la **evasión preventiva** evalúa las peticiones **antes** de otorgar el recurso:
* Construye dinámicamente las matrices de:
  $$\text{Need}[i][j] = \text{Max}[i][j] - \text{Allocation}[i][j]$$
* Simula una asignación provisional (*Pretend Allocation*).
* Ejecuta el Algoritmo de Seguridad: verifica si existe al menos una **Secuencia Segura** de ejecución que permita a todos los procesos terminar.
* Si el estado resultante es **Seguro**, se concede el recurso. Si es **Inseguro**, se rechaza temporalmente y el proceso se mantiene en `ESPERANDO`.

---

## 📈 8. Tabla Oficial de 9 Métricas de Auditoría

Al concluir cualquier simulación, el módulo `metrics.py` procesa y renderiza la siguiente tabla con formato enriquecido:

| # | Métrica | Fuente de Datos | Criterio de Aprobación |
| :---: | :--- | :--- | :--- |
| **1** | Total de procesos simulados | `len(processes)` | Coincide exactamente con el JSON cargado. |
| **2** | Procesos terminados exitosamente | Filtro `state == TERMINADO` | Procesos que agotaron sus acciones y devolvieron recursos. |
| **3** | Procesos bloqueados residuales | Filtro `state in (ESPERANDO, BLOQUEADO)` | Procesos que no pudieron concluir por contención crítica. |
| **4** | Pico máximo de memoria consumida | `memory_manager.peak_memory_used` | Máximo histórico de memoria RAM asignada en MB. |
| **5** | Total de solicitudes de recursos | `resource_manager.total_requests` | Conteo acumulado de peticiones `request_resource`. |
| **6** | Frecuencia de espera de procesos | `resource_manager.wait_transitions` | Transiciones de procesos hacia el estado `ESPERANDO`. |
| **7** | Interbloqueos detectados vs. resueltos | `deadlock_history` y `banker_strategy` | Valida la eficacia del Banquero en mitigar deadlocks. |
| **8** | Recursos involucrados en deadlocks | Nombres de nodos en ciclos del RAG | Identificadores exactos de los dispositivos atascados. |
| **9** | Balance de liberación final | Recursos liberados vs. retenidos | Auditoría: debe certificar ausencia de fugas de recursos. |

---

## 🧪 9. Pruebas de Blindaje y Estrés (*Escenario Sorpresa*)

Para garantizar que el simulador supere la prueba docente sin depender de ningún identificador preconcebido, se diseñó la suite automatizada `test_stress_surprise.py`.

### Ejecución de la Suite de Pruebas:
```bash
python test_stress_surprise.py
```

### Lo que valida automáticamente:
1. **Generación Aleatoria:** Crea escenarios con nombres estocásticos (`Worker_Theta_42`, `GPU_Titan_9`, etc.).
2. **Resistencia a JSONs Malformados:** Comprueba que campos faltantes o errores de sintaxis arrojen excepciones controladas y no tiren el simulador.
3. **Concurrencia en Archivos Virtuales:** Intenta lecturas y escrituras simultáneas sobre el mismo archivo para verificar los cerrojos (*locks*).
4. **Validación de Coffman y Banquero:** Valida que el detector marque interbloqueo ante esperas circulares y que el banquero evite el bloqueo en el mismo escenario.

---

## 👥 10. Créditos y Trabajo Colaborativo en Git

El proyecto fue desarrollado mediante la metodología de ramas de características (*feature branches*) y revisión de código por Pull Request:
* `feature/procesos-y-logs` (Uriel)
* `feature/memoria-y-monitoreo` (Chris)
* `feature/file-manager` (Daniel)
* `feature/resource_manager` (Uriel)
* `feature/simulator-modos` (Chris)
* `feature/cli-interface` (Daniel)
* `feature/scenarios-y-metrics` (Daniel)
* `feature/visualizacion-grafo` (Chris)
* `feature/pruebas-y-readme` (Daniel)

Repositorio oficial: [DanyFlow06/Proyecto-Parcial-1](https://github.com/DanyFlow06/Proyecto-Parcial-1)
