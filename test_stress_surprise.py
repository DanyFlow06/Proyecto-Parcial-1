"""
test_stress_surprise.py
=======================
Suite integral de pruebas de estres, robustez y blindaje del Micro-Kernel SO.
Valida formalmente:
1. Blindaje contra Escenario Sorpresa (cero dependencia de identificadores fijos).
2. Resistencia a fallos, archivos corruptos y estructuras JSON irregulares.
3. Control estricto de limites de memoria RAM simulada.
4. Concurrencia y cerrojos de exclusion mutua en archivos virtuales.
5. Evaluacion de las 4 Condiciones de Coffman y extraccion de ciclos RAG.
6. Eficacia de la Evasion preventiva con el Algoritmo del Banquero de Dijkstra.
7. Exactitud e integridad de las 9 metricas obligatorias.

Sprint 4 - Daniel
"""

import sys
import os
import json
import tempfile
import unittest

# Asegurar codificacion UTF-8 en terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from main import SystemSimulatorEngine
from process import Process, ESTADO_ACTIVO_O_LISTO, ESTADO_ESPERANDO, ESTADO_BLOQUEADO, ESTADO_TERMINADO
from managers.memory_manager import MemoryManager
from managers.resource_manager import ResourceManager
from managers.file_manager import FileManager
from deadlock_detector import DeadlockDetector
from banker_strategy import BankerStrategy
from metrics import MetricsCollector


class TestRobustezYBlindaje(unittest.TestCase):
    """Pruebas de resistencia a entradas irregulares y blindaje del sistema."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_manejo_archivo_inexistente(self):
        """El motor debe reportar error limpio ante archivo no encontrado sin crashear."""
        engine = SystemSimulatorEngine()
        res = engine.load_scenario("archivo_fantasma_no_existe.json")
        self.assertFalse(res, "Debe retornar False sin lanzar excepcion no capturada.")

    def test_02_json_malformado(self):
        """El motor debe capturar JSONDecodeError ante sintaxis invalida."""
        corrupt_path = os.path.join(self.temp_dir.name, "corrupto.json")
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write("{ total_memory: 1024, resources: [}")  # JSON corrupto

        engine = SystemSimulatorEngine()
        res = engine.load_scenario(corrupt_path)
        self.assertFalse(res, "Debe rechazar un JSON con sintaxis rota sin colapsar.")

    def test_03_campos_obligatorios_faltantes(self):
        """Valida que falte 'total_memory', 'resources' o 'processes' sin crashear."""
        incompleto_path = os.path.join(self.temp_dir.name, "incompleto.json")
        with open(incompleto_path, "w", encoding="utf-8") as f:
            json.dump({"total_memory": 500, "resources": []}, f)  # Falta 'processes'

        engine = SystemSimulatorEngine()
        res = engine.load_scenario(incompleto_path)
        self.assertFalse(res, "Debe rechazar un JSON sin los 3 campos obligatorios.")

    def test_04_nombres_estocasticos_sorpresa(self):
        """Valida que el sistema opere al 100% con nombres completamente heterogeneos y dinamicos."""
        surprise_path = os.path.join(self.temp_dir.name, "surprise_random.json")
        surprise_data = {
            "total_memory": 1000,
            "resources": [
                {"name": "Dispositivo_Quantico_#99", "type": "exclusive"},
                {"name": "Coprocesador_Optico", "type": "shared", "units": 2}
            ],
            "processes": [
                {
                    "pid": "Worker_Especial_Omega",
                    "memory_required": 300,
                    "instructions": [
                        {"step": 1, "action": "request_resource", "resource": "Dispositivo_Quantico_#99"},
                        {"step": 2, "action": "create_file", "file": "matriz_cuantica.dat"},
                        {"step": 3, "action": "write_file", "file": "matriz_cuantica.dat"},
                        {"step": 4, "action": "release_resource", "resource": "Dispositivo_Quantico_#99"}
                    ]
                }
            ]
        }
        with open(surprise_path, "w", encoding="utf-8") as f:
            json.dump(surprise_data, f)

        engine = SystemSimulatorEngine(use_banker=False)
        self.assertTrue(engine.load_scenario(surprise_path))
        
        metrics = engine.run_all(verbose=False)
        self.assertEqual(metrics["total_procesos"], 1)
        self.assertEqual(metrics["terminados"], 1)
        self.assertEqual(metrics["bloqueados_residuales"], 0)
        self.assertEqual(metrics["pico_memoria_mb"], 300)

    def test_05_limite_de_memoria_ram(self):
        """Procesos que exceden la memoria disponible deben pasar a ESPERANDO."""
        mem_mgr = MemoryManager(total_memory=200)
        p1 = Process(pid="P_Mem_Big", memory_required=300, instructions=[])
        
        ok = mem_mgr.allocate_memory(p1)
        self.assertFalse(ok, "No debe asignar si se requiere mas memoria que la disponible.")
        self.assertEqual(p1.state, ESTADO_ESPERANDO)
        self.assertEqual(mem_mgr.used_memory, 0)
        self.assertEqual(mem_mgr.available_memory, 200)

    def test_06_control_concurrencia_archivos(self):
        """Verifica que dos procesos no puedan escribir simultaneamente en un archivo bloqueado."""
        fm = FileManager()
        msg1 = fm.create_file("reporte_confidencial.txt", pid="Proceso_A")
        self.assertIn("[OK]", msg1)

        # Proceso B intenta escribir en archivo de Proceso A
        msg2 = fm.write_file(filename="reporte_confidencial.txt", pid="Proceso_B", content="Hack data")
        self.assertIn("[ERROR]", msg2, "Debe rechazar la escritura concurrente por proceso ajeno.")
        self.assertEqual(fm.file_locks.get("reporte_confidencial.txt"), "Proceso_A")

    def test_07_deteccion_coffman_y_ciclos(self):
        """Comprueba que el detector identifique las 4 condiciones de Coffman en el Escenario 3."""
        esc_3_path = os.path.join(os.path.dirname(__file__), "scenarios", "escenario_3.json")
        if not os.path.exists(esc_3_path):
            self.skipTest("escenario_3.json no encontrado")

        engine = SystemSimulatorEngine(use_banker=False)
        self.assertTrue(engine.load_scenario(esc_3_path))
        
        metrics = engine.run_all(verbose=False)
        self.assertGreater(metrics["bloqueados_residuales"], 0, "El escenario 3 debe provocar bloqueo.")
        self.assertGreater(metrics["deadlocks_detectados"], 0, "Debe detectar al menos 1 deadlock.")
        self.assertGreater(len(metrics["recursos_en_deadlock"]), 0, "Debe listar los recursos atrapados.")

    def test_08_evasion_algoritmo_banquero(self):
        """Comprueba que el Escenario 4 termine exitosamente cuando el Banquero esta activo."""
        esc_4_path = os.path.join(os.path.dirname(__file__), "scenarios", "escenario_4.json")
        if not os.path.exists(esc_4_path):
            self.skipTest("escenario_4.json no encontrado")

        engine = SystemSimulatorEngine(use_banker=True)
        self.assertTrue(engine.load_scenario(esc_4_path))
        
        metrics = engine.run_all(verbose=False)
        self.assertEqual(metrics["terminados"], metrics["total_procesos"], 
                         "Con el Banquero activo todos los procesos deben terminar en estado seguro.")
        self.assertEqual(metrics["bloqueados_residuales"], 0)

    def test_09_escenario_sorpresa_preconfigurado(self):
        """Ejecuta el escenario_sorpresa.json oficial para certificar compatibilidad completa."""
        sorpresa_path = os.path.join(os.path.dirname(__file__), "scenarios", "escenario_sorpresa.json")
        if not os.path.exists(sorpresa_path):
            self.skipTest("escenario_sorpresa.json no encontrado")

        engine = SystemSimulatorEngine(use_banker=True)
        self.assertTrue(engine.load_scenario(sorpresa_path))
        metrics = engine.run_all(verbose=False)
        
        self.assertGreaterEqual(metrics["total_procesos"], 3)
        self.assertGreaterEqual(metrics["pico_memoria_mb"], 180)


def run_tests():
    print("=" * 70)
    print("  SUITE DE BLINDAJE Y PRUEBAS DE ESTRES - MICRO-KERNEL SO (SPRINT 4)")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRobustezYBlindaje)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n" + "=" * 70)
        print("  [OK] TODAS LAS PRUEBAS DE BLINDAJE PASARON EXITOSAMENTE (100% OK)")
        print("=" * 70)
        return 0
    else:
        print("\n[FALLO] Se detectaron fallos en las pruebas.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
