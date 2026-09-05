"""
cli_interface.py
================
Interfaz visual de terminal con la libreria Rich.
Renderiza tablas de procesos coloreadas por estado, barra de memoria RAM,
tabla de asignacion de recursos, panel de archivos virtuales y hardware real.

Sprint 2 - Daniel
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.bar import Bar
from rich.text import Text
from rich.prompt import Prompt
from rich import box

from monitoring import get_hardware_status

# Instancia global de la consola Rich
console = Console()

# ─── Mapa de colores por estado del proceso ────────────────────────────────────
COLORES_ESTADO = {
    "ACTIVO_O_LISTO": "green",
    "ESPERANDO":      "yellow",
    "BLOQUEADO":      "red",
    "TERMINADO":      "dim",
}


# ── 1. Tabla de procesos ──────────────────────────────────────────────────────
def mostrar_tabla_procesos(processes):
    """
    Muestra una tabla con todos los procesos, coloreada por estado.

    Parametros:
        processes (list[Process]): Lista de objetos Process.
    """
    table = Table(
        title="Tabla de Procesos",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("PID", style="bold", justify="center")
    table.add_column("Estado", justify="center")
    table.add_column("RAM (MB)", justify="right")
    table.add_column("Recursos Retenidos", justify="left")
    table.add_column("Acciones Pendientes", justify="right")

    for p in processes:
        color = COLORES_ESTADO.get(p.state, "white")
        recursos = ", ".join(p.resources_held) if p.resources_held else "-"
        pendientes = str(len(p.pending_actions))

        table.add_row(
            f"[{color}]{p.pid}[/{color}]",
            f"[{color}]{p.state}[/{color}]",
            f"[{color}]{p.memory_required}[/{color}]",
            f"[{color}]{recursos}[/{color}]",
            f"[{color}]{pendientes}[/{color}]",
        )

    console.print(table)


# ── 2. Barra de memoria ──────────────────────────────────────────────────────
def mostrar_barra_memoria(memory_manager):
    """
    Muestra una barra de progreso visual con el uso de memoria RAM simulada.

    Parametros:
        memory_manager (MemoryManager): Instancia del administrador de memoria.
    """
    total = memory_manager.total_memory
    used = memory_manager.used_memory
    available = memory_manager.available_memory
    peak = memory_manager.peak_memory_used

    # Calcular porcentaje de uso
    if total > 0:
        pct = (used / total) * 100
    else:
        pct = 0

    # Color dinamico segun el nivel de uso
    if pct < 50:
        bar_color = "green"
    elif pct < 80:
        bar_color = "yellow"
    else:
        bar_color = "red"

    # Construir texto visual de la barra (caracteres ASCII para compatibilidad Windows)
    bar_width = 40
    filled = int((pct / 100) * bar_width)
    empty = bar_width - filled
    bar_visual = f"[{bar_color}]{'#' * filled}[/{bar_color}][dim]{'-' * empty}[/dim]"

    info = (
        f"  {bar_visual}  {pct:.1f}%\n\n"
        f"  [bold]Total:[/bold]       {total} MB\n"
        f"  [bold]Usada:[/bold]       {used} MB\n"
        f"  [bold]Disponible:[/bold]  {available} MB\n"
        f"  [bold]Pico Maximo:[/bold] {peak} MB"
    )

    panel = Panel(
        info,
        title="Memoria RAM Simulada",
        border_style=bar_color,
        box=box.ROUNDED,
    )
    console.print(panel)


# ── 3. Tabla de recursos ─────────────────────────────────────────────────────
def mostrar_tabla_recursos(resource_manager=None):
    """
    Muestra la tabla de asignacion de recursos exclusivos y compartidos.

    Si resource_manager es None (aun no implementado por Uriel), muestra un
    panel informativo en su lugar.

    Parametros:
        resource_manager: Instancia del ResourceManager (o None).
    """
    if resource_manager is None:
        panel = Panel(
            "[dim italic]ResourceManager no conectado aun.\n"
            "Se mostrara la tabla cuando el modulo este disponible.[/dim italic]",
            title="Asignacion de Recursos",
            border_style="dim",
            box=box.ROUNDED,
        )
        console.print(panel)
        return

    # Cuando resource_manager exista, se espera que tenga:
    # - resource_manager.resources: dict con info de cada recurso
    # - resource_manager.allocation: dict {recurso: pid o None}
    # - resource_manager.waiting_queues: dict {recurso: [pids]}
    table = Table(
        title="Asignacion de Recursos",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("Recurso", style="bold", justify="left")
    table.add_column("Tipo", justify="center")
    table.add_column("Asignado a (PID)", justify="center")
    table.add_column("Cola de Espera", justify="left")

    # Se adapta al atributo que exponga resource_manager
    try:
        for res_name, res_info in resource_manager.resources.items():
            tipo = res_info.get("type", "exclusivo")
            asignado = resource_manager.allocation.get(res_name)
            asignado_str = str(asignado) if asignado else "[dim]-[/dim]"
            cola = resource_manager.waiting_queues.get(res_name, [])
            cola_str = ", ".join(str(p) for p in cola) if cola else "[dim]-[/dim]"

            # Colorear segun estado
            if asignado and cola:
                row_color = "yellow"
            elif asignado:
                row_color = "green"
            else:
                row_color = "dim"

            table.add_row(
                f"[{row_color}]{res_name}[/{row_color}]",
                f"[{row_color}]{tipo}[/{row_color}]",
                asignado_str,
                cola_str,
            )
    except AttributeError:
        table.add_row("[red]Error al leer ResourceManager[/red]", "-", "-", "-")

    console.print(table)


# ── 4. Tabla de archivos virtuales ────────────────────────────────────────────
def mostrar_tabla_archivos(file_manager):
    """
    Muestra la tabla de archivos del sistema virtual con sus bloqueos.

    Parametros:
        file_manager (FileManager): Instancia del administrador de archivos.
    """
    status = file_manager.get_status()

    table = Table(
        title="Sistema de Archivos Virtual",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("Archivo", style="bold", justify="left")
    table.add_column("Contenido", justify="left", max_width=30)
    table.add_column("Bloqueado por (PID)", justify="center")

    if file_manager.filesystem:
        for filename, data in file_manager.filesystem.items():
            content = data.get("content", "")
            preview = content[:50] + "..." if len(content) > 50 else content
            if not preview:
                preview = "[dim]<vacio>[/dim]"

            lock_pid = file_manager.file_locks.get(filename)
            if lock_pid is not None:
                lock_str = f"[yellow]PID={lock_pid}[/yellow]"
            else:
                lock_str = "[green]Libre[/green]"

            table.add_row(filename, preview, lock_str)
    else:
        table.add_row("[dim]Sin archivos[/dim]", "-", "-")

    console.print(table)

    # Estadisticas debajo de la tabla
    stats = (
        f"  [bold]Archivos totales:[/bold] {status['total_files']}  |  "
        f"[bold]Operaciones:[/bold] {status['total_operations']}  |  "
        f"[bold]Fallidas:[/bold] {status['failed_operations']}"
    )
    console.print(Panel(stats, border_style="dim", box=box.SIMPLE))


# ── 5. Panel de hardware real ─────────────────────────────────────────────────
def mostrar_hardware():
    """
    Muestra el estado real del hardware del equipo anfitrion usando psutil.
    """
    try:
        hw = get_hardware_status()

        info = (
            f"  [bold]CPU:[/bold]              {hw['cpu_percent']}%\n"
            f"  [bold]RAM Fisica:[/bold]        {hw['ram_percent']}%\n"
            f"  [bold]Disco Libre:[/bold]       {hw['disk_free_gb']} GB\n"
            f"  [bold]Red Enviados:[/bold]      {hw['network_bytes_sent']:,} bytes\n"
            f"  [bold]Red Recibidos:[/bold]     {hw['network_bytes_recv']:,} bytes"
        )

        panel = Panel(
            info,
            title="Hardware Real (psutil)",
            border_style="blue",
            box=box.ROUNDED,
        )
        console.print(panel)

    except Exception as e:
        console.print(
            Panel(
                f"[red]Error al leer hardware: {e}[/red]",
                title="Hardware Real",
                border_style="red",
            )
        )


# ── 6. Dashboard unificado ───────────────────────────────────────────────────
def mostrar_dashboard(processes, memory_manager, file_manager, resource_manager=None):
    """
    Muestra un dashboard completo con todos los paneles del sistema.
    Ideal para llamar en cada tick del simulador (modo paso a paso).

    Parametros:
        processes (list[Process]):        Lista de procesos activos.
        memory_manager (MemoryManager):   Administrador de memoria.
        file_manager (FileManager):       Administrador de archivos.
        resource_manager (opcional):      Administrador de recursos (None si no existe aun).
    """
    console.clear()
    console.rule("[bold cyan]Dashboard del Simulador SO[/bold cyan]", style="cyan")
    console.print()

    mostrar_tabla_procesos(processes)
    console.print()

    mostrar_barra_memoria(memory_manager)
    console.print()

    mostrar_tabla_recursos(resource_manager)
    console.print()

    mostrar_tabla_archivos(file_manager)
    console.print()

    mostrar_hardware()

    console.rule(style="cyan")


# ── 7. Menu principal interactivo ─────────────────────────────────────────────
def mostrar_menu_principal():
    """
    Despliega el menu principal del simulador y retorna la opcion seleccionada.

    Retorna:
        str: La opcion elegida por el usuario ("1" a "6").
    """
    console.print()
    console.rule("[bold cyan]Simulador de Sistema Operativo[/bold cyan]", style="cyan")

    menu_text = (
        "\n"
        "  [bold]1.[/bold] Cargar escenario JSON\n"
        "  [bold]2.[/bold] Ejecutar en Modo Automatico\n"
        "  [bold]3.[/bold] Ejecutar en Modo Paso a Paso\n"
        "  [bold]4.[/bold] Ver estado del sistema (Dashboard)\n"
        "  [bold]5.[/bold] Ver hardware real\n"
        "  [bold]6.[/bold] Salir\n"
    )

    panel = Panel(
        menu_text,
        title="Menu Principal",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)

    opcion = Prompt.ask(
        "[bold cyan]Selecciona una opcion[/bold cyan]",
        choices=["1", "2", "3", "4", "5", "6"],
        default="6",
    )

    return opcion
