import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def render_rag(processes_list, resources_held, resources_waiting, deadlock_cycle=None):
    """
    Construye y renderiza el Grafo de Asignación de Recursos (RAG).
    
    :param processes_list: Lista de identificadores de procesos (ej. ['P1', 'P2'])
    :param resources_held: Dict mapeando proceso a lista de recursos que posee (ej. {'P1': ['Impresora_1']})
    :param resources_waiting: Dict mapeando proceso a lista de recursos que está esperando (ej. {'P1': ['Scanner_1']})
    :param deadlock_cycle: Lista de tuplas de aristas que forman el deadlock (ej. [('P1', 'Scanner_1'), ('Scanner_1', 'P2'), ...])
                           Se pintarán de rojo automáticamente.
    """
    G = nx.DiGraph()
    
    # Identificar todos los recursos únicos
    all_resources = set()
    for res_list in resources_held.values():
        all_resources.update(res_list)
    for res_list in resources_waiting.values():
        all_resources.update(res_list)
        
    # 1. Añadir Nodos
    # Procesos (Circulares, Azules) y Recursos (Cuadrados, Anaranjados)
    G.add_nodes_from(processes_list, type='process')
    G.add_nodes_from(all_resources, type='resource')
    
    # 2. Añadir Aristas
    edges_normal = []
    
    # Flecha: Recurso -> Proceso (Significa que el recurso está asignado al proceso)
    for proc, res_list in resources_held.items():
        for res in res_list:
            edges_normal.append((res, proc))
            
    # Flecha: Proceso -> Recurso (Significa que el proceso está esperando el recurso)
    for proc, res_list in resources_waiting.items():
        for res in res_list:
            edges_normal.append((proc, res))
            
    G.add_edges_from(edges_normal)
    
    # Determinar qué aristas van en color rojo (las que forman el ciclo de interbloqueo)
    deadlock_edges = set(deadlock_cycle) if deadlock_cycle else set()
    
    # Clasificar aristas para el renderizado
    edges_red = [e for e in G.edges() if e in deadlock_edges or (e[1], e[0]) in deadlock_edges]
    edges_black = [e for e in G.edges() if e not in edges_red]
    
    # Limpiar figura actual por si se llama varias veces durante el simulador
    plt.clf()
    
    # Calcular posiciones (Layout) para organizar los nodos visualmente
    pos = nx.spring_layout(G, seed=42, k=0.9)
    
    # Dibujar Nodos de Procesos (Círculos azules)
    nx.draw_networkx_nodes(G, pos, 
                           nodelist=processes_list, 
                           node_color='skyblue', 
                           node_shape='o', 
                           node_size=1200, 
                           edgecolors='black')
                           
    # Dibujar Nodos de Recursos (Cuadrados anaranjados)
    nx.draw_networkx_nodes(G, pos, 
                           nodelist=list(all_resources), 
                           node_color='orange', 
                           node_shape='s', 
                           node_size=1000, 
                           edgecolors='black')
                           
    # Dibujar etiquetas de los nombres
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
    
    # Dibujar aristas normales (Negras)
    if edges_black:
        nx.draw_networkx_edges(G, pos, edgelist=edges_black, edge_color='black',
                               arrows=True, arrowstyle='-|>', arrowsize=20, width=1.5)
                               
    # Dibujar aristas de interbloqueo (Rojas)
    if edges_red:
        nx.draw_networkx_edges(G, pos, edgelist=edges_red, edge_color='red',
                               arrows=True, arrowstyle='-|>', arrowsize=25, width=2.5)
                               
    # Crear Leyenda visual para que sea fácil de entender
    patch_proc = mpatches.Patch(color='skyblue', label='Procesos')
    patch_res = mpatches.Patch(color='orange', label='Recursos')
    patch_edge = mpatches.Patch(color='black', label='Asignación / Petición')
    
    legend_handles = [patch_proc, patch_res, patch_edge]
    
    # Títulos condicionales según si hay interbloqueo o no
    if edges_red:
        patch_deadlock = mpatches.Patch(color='red', label='Ciclo de Interbloqueo')
        legend_handles.append(patch_deadlock)
        plt.title("¡ALERTA DE INTERBLOQUEO DETECTADO!", color='red', fontweight='bold', fontsize=14)
    else:
        plt.title("Grafo de Asignación de Recursos (RAG)", fontweight='bold', fontsize=14)
        
    plt.legend(handles=legend_handles, loc='best')
    plt.axis('off')
    
    # Mostrar la ventana emergente interactiva
    # (Pausa la ejecución del script hasta que el usuario cierre la ventana de Matplotlib)
    plt.show()

# Bloque de prueba (Solo se ejecuta si corres este archivo directamente)
if __name__ == "__main__":
    # Datos de prueba simulando el Escenario 3 (Interbloqueo Real)
    test_procs = ["P1", "P2", "P3"]
    test_held = {"P1": ["Impresora"], "P2": ["Scanner"]}
    test_waiting = {"P1": ["Scanner"], "P2": ["Impresora"]}
    
    # El ciclo forma: Impresora -> P1 -> Scanner -> P2 -> Impresora
    test_cycle = [("Impresora", "P1"), ("P1", "Scanner"), ("Scanner", "P2"), ("P2", "Impresora"), ("P3, Scanner")]
    
    print("Mostrando grafo de prueba. Cierra la ventana para terminar.")
    render_rag(test_procs, test_held, test_waiting, test_cycle)

