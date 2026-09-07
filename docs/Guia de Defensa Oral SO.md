# 🎓 Guía Maestra de Preparación para la Defensa Oral del Proyecto

> **Asignatura:** Sistemas Operativos  
> **Proyecto:** Micro-Kernel: Administrador de Recursos, Detección de Deadlocks y Evasión con el Algoritmo del Banquero  
> **Equipo:** Uriel (Líder / PR Reviewer), Chris, Daniel  
> **Documento:** Acordeón Técnico, Preguntas Frecuentes de Examen y Guion de Demostración en Vivo

---

## ⏱️ 1. Pitch de Apertura del Equipo (2 Minutos)

> *"Buenas tardes profesora. Nuestro proyecto consiste en un **simulador discreto del núcleo de un Sistema Operativo multiprogramado** desarrollado en Python.  
> Su propósito central no es administrar el hardware real del equipo, sino **modelar la competencia concurrente entre múltiples procesos por recursos finitos**: memoria RAM simulada, dispositivos exclusivos y compartidos, y archivos virtuales en memoria.  
> El núcleo del sistema implementa de forma rigurosa la teoría de interbloqueos (*deadlocks*):
> 1. Modela el ciclo de vida de los procesos a través de sus **4 estados canónicos** (`ACTIVO_O_LISTO`, `ESPERANDO`, `BLOQUEADO`, `TERMINADO`).
> 2. Evalúa programáticamente en cada tick las **4 Condiciones de Coffman** y construye el **Grafo de Asignación de Recursos (RAG)** dirigido bipartito con `networkx`, resaltando ciclos críticos en color rojo.
> 3. Implementa el **Algoritmo del Banquero de Dijkstra** para la **evasión preventiva** de interbloqueos, evaluando estados de seguridad antes de conceder cualquier asignación.
> 4. Todo el código está modularizado en el paquete `managers/`, es **100% dinámico y blindado frente a cualquier Escenario Sorpresa**, y mapea sus operaciones con llamadas al sistema reales de POSIX."*

---

## 🧠 2. Preguntas Teóricas Clave y Respuestas Ideales

### Pregunta 1: ¿Qué es un interbloqueo (*deadlock*) y por qué ocurre?
* **Respuesta:** Un interbloqueo es una situación en la que un conjunto de dos o más procesos quedan bloqueados de forma permanente e indefinida porque cada uno retiene un recurso que el otro necesita para continuar su ejecución, formando una dependencia circular imposible de satisfacer sin intervención externa.

---

### Pregunta 2: ¿Cuáles son las 4 Condiciones de Coffman y cómo las evalúa nuestro código?
* **Respuesta:** Edward G. Coffman demostró en 1971 que para que ocurra un deadlock deben cumplirse simultáneamente 4 condiciones:
  1. **Exclusión Mutua (*Mutual Exclusion*):** Al menos un recurso no es compartible. En nuestro código, `resource_manager.py` define recursos de tipo `exclusive` que solo pueden tener asignadas unidades a un solo PID.
  2. **Retención y Espera (*Hold and Wait*):** Un proceso retiene recursos y al mismo tiempo solicita otros adicionales. En `deadlock_detector.py`, se evalúa si un nodo de proceso en el grafo RAG tiene grado de entrada $\text{in\_degree} > 0$ (retiene) y grado de salida $\text{out\_degree} > 0$ (espera).
  3. **No Expropiación (*No Preemption*):** El sistema operativo no le arrebata recursos a los procesos por la fuerza; solo los liberan voluntariamente con `release_resource`.
  4. **Espera Circular (*Circular Wait*):** Existe un ciclo cerrado en el Grafo de Asignación de Recursos ($P_1 \to R_1 \to P_2 \to R_2 \to P_1$). Se evalúa con `nx.simple_cycles(rag)`.

---

### Pregunta 3: ¿Por qué un Estado Inseguro en el Banquero NO es necesariamente un Deadlock?
* **Respuesta:** 
  * Un **Estado Seguro** es aquel en el que existe al menos una **Secuencia Segura** de ejecución $\langle P_1, P_2, \dots, P_n \rangle$ tal que, si cada proceso solicitara su demanda máxima declarada, el sistema garantiza que todos podrán terminar.
  * Un **Estado Inseguro** significa que el sistema **no puede garantizar** que todos los procesos terminarán si todos piden su máximo al mismo tiempo. Es decir, el estado inseguro es un estado de **riesgo potencial**, no un interbloqueo consumado; sin embargo, si un proceso continúa solicitando recursos en estado inseguro, inevitablemente caerá en deadlock.
  * Por eso el **Algoritmo del Banquero evade** el problema negando provisionalmente solicitudes que lleven a estados inseguros.

---

### Pregunta 4: ¿Cómo se construyen las matrices del Algoritmo del Banquero?
* **Respuesta:** En `banker_strategy.py`, para $n$ procesos y $m$ recursos:
  * **$\text{Available}[j]$:** Vector de unidades disponibles libres de cada recurso $j$.
  * **$\text{Allocation}[i][j]$:** Unidades del recurso $j$ actualmente en poder del proceso $i$.
  * **$\text{Max}[i][j]$:** Demanda máxima declarada por el proceso $i$. Se calcula inspeccionando las instrucciones futuras (`pending_actions`) más lo ya asignado.
  * **$\text{Need}[i][j]$:** Matriz de necesidad:
    $$\text{Need}[i][j] = \text{Max}[i][j] - \text{Allocation}[i][j]$$
  * El algoritmo simula la asignación y busca un proceso con $\text{Need}[i] \le \text{Work}$. Si lo encuentra, asume que termina y suma sus recursos devueltos a $\text{Work} = \text{Work} + \text{Allocation}[i]$. Si logra completar la secuencia para todos los procesos, el estado es **Seguro**.

---

### Pregunta 5: ¿Qué llamadas al sistema reales (Syscalls) modela nuestro simulador?
* **Respuesta:**
  1. **`brk()` / `mmap()`:** Solicitud de memoria RAM simulada en `MemoryManager`. Modifica el límite del heap del proceso o reserva páginas virtuales.
  2. **`creat()` / `open(O_CREAT)`:** Creación de archivos virtuales en `FileManager`. Crea un inodo en el VFS.
  3. **`read()` / `write()`:** Lectura y escritura de contenido en `FileManager`, manejando buffers y locks de exclusión mutua.
  4. **`unlink()`:** Eliminación de archivos virtuales en `FileManager`, liberando la estructura en memoria cuando no hay locks.
  5. **`sem_wait()` / `pthread_mutex_lock()`:** Solicitud de recursos exclusivos en `ResourceManager`. Bloquea el hilo/proceso en una cola FIFO si el contador es cero.

---

### Pregunta 6: ¿Cuáles son las 4 Capas del Sistema Operativo en nuestro proyecto?
* **Respuesta:**
  1. **Capa 1: Aplicación:** El archivo de escenario JSON y las instrucciones del proceso (`request_resource`, `create_file`).
  2. **Capa 2: Shell / CLI:** `main.py` y `cli_interface.py` que parsean la entrada, muestran paneles de Rich y recogen comandos del usuario.
  3. **Capa 3: Kernel:** Los gestores en `managers/` (`MemoryManager`, `ResourceManager`, `FileManager`), el detector de Coffman y el Algoritmo del Banquero.
  4. **Capa 4: Hardware:** 
     * **Hardware Simulado:** RAM virtual y periféricos virtuales.
     * **Hardware Real:** Monitoreo con la biblioteca `psutil` (CPU %, RAM física, disco y red del equipo anfitrión).

---

### Pregunta 7: ¿Cómo garantizan que el código soporta el "Escenario Sorpresa"?
* **Respuesta:** El código está completamente parametrizado y desacoplado. No existe ninguna línea de código que compare cadenas como `if pid == "P1"` o `if resource == "Impresora"`. Los diccionarios y grafos se crean a partir de las llaves del JSON dinámicamente. Además, creamos la suite `test_stress_surprise.py` que genera escenarios con nombres aleatorios y valida que el sistema opere al 100% de forma determinista.

---

## 🎬 3. Guion Sugerido de Demostración en Vivo (Paso a Paso)

Si la docente pide correr el proyecto, sigan este orden de 4 pasos:

### Paso 1: Demostrar Ejecución Normal (Escenario 1)
```bash
python main.py --scenario scenarios/escenario_1.json --mode auto
```
* **Qué explicar:** Observen la tabla de procesos y las 9 métricas. 3 procesos con memoria suficiente, operaciones de archivos limpias y 0 deadlocks.

### Paso 2: Demostrar Espera Temporal sin Deadlock (Escenario 2)
```bash
python main.py --scenario scenarios/escenario_2.json --mode auto
```
* **Qué explicar:** Dos procesos compiten por el mismo recurso. La métrica 6 muestra cómo un proceso entra a `ESPERANDO`, pero cuando el primero libera el recurso, la cola FIFO despierta al segundo y concluye con 0 deadlocks (sin falsos positivos).

### Paso 3: Demostrar Detección de Deadlock y Grafo Rojo (Escenario 3)
```bash
python main.py --scenario scenarios/escenario_3.json --mode auto --rag
```
* **Qué explicar:** Aquí se produce una espera circular pura. El simulador detecta las 4 condiciones de Coffman, transiciona los procesos a `BLOQUEADO` y abre la ventana interactiva de Matplotlib mostrando el ciclo dirigido con aristas en **rojo**.

### Paso 4: Demostrar Evasión con el Banquero (Escenario 4)
* **Primero correr SIN banquero:**
  ```bash
  python main.py --scenario scenarios/escenario_4.json --mode auto
  ```
  *(Mostrar cómo colapsa en interbloqueo).*
* **Luego correr CON banquero:**
  ```bash
  python main.py --scenario scenarios/escenario_4.json --mode auto --banker
  ```
  *(Mostrar cómo el Banquero deniega la petición insegura, pone al proceso en espera, y todos los procesos terminan al 100% con 0 procesos bloqueados).*

### Paso 5: Demostrar el Escenario Sorpresa y Suite de Pruebas
```bash
python test_stress_surprise.py
```
* **Qué explicar:** Se ejecutan las 9 pruebas de resistencia, validando tolerancia a fallos, concurrencia de archivos, límites de memoria y nombres no convencionales con 100% de aprobación.
