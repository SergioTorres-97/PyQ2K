from qual2k.core.model import Q2KModel
from pathlib import Path
import pygad
import warnings
import os
import glob
import shutil
import tempfile
import multiprocessing as mp
from functools import partial

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACIÓN BASE
# ============================================================================
base = Path(__file__).parent.parent
filepath = f'{base}/data/templates/Chicamocha'
header_dict = {
    "version": "v2.12",
    "rivname": "Chicamocha",
    "filename": "Chicamocha",
    "filedir": filepath,
    "applabel": "Chicamocha (6/27/2012)",
    "xmon": 6,
    "xday": 27,
    "xyear": 2012,
    "timezonehour": -6,
    "pco2": 0.000347,
    "dtuser": 4.16666666666667E-03,
    "tf": 5,
    "IMeth": "Euler",
    "IMethpH": "Brent"
}

# Obtener número de reaches
model_temp = Q2KModel(filepath, header_dict)
model_temp.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')
n = len(model_temp.data_reaches)
print(f'Número de reaches: {n}')

# ============================================================================
# CONFIGURACIÓN DE PARALELIZACIÓN
# ============================================================================
NUM_WORKERS = min(4, mp.cpu_count() - 1)  # Deja 1 CPU libre
USAR_PARALELO = True  # Cambia a False para modo serial (debug)

print(f'Modo: {"PARALELO" if USAR_PARALELO else "SERIAL"}')
if USAR_PARALELO:
    print(f'Workers: {NUM_WORKERS}')

# ============================================================================
# PARÁMETROS A CALIBRAR
# ============================================================================
parametros = {
    'kaaa': (0.1, 2, False),
    'kn': (0.0005, 0.01, False),
    'kdc': (0.1, 1.5, False),
}

# ============================================================================
# CREAR GENE_SPACE Y MAPEO
# ============================================================================
gene_space = []
param_map = []

for param_name, (min_val, max_val, is_global) in parametros.items():
    if is_global:
        gene_space.append({'low': min_val, 'high': max_val})
        param_map.append((param_name, None))
    else:
        for i in range(n):
            gene_space.append({'low': min_val, 'high': max_val})
            param_map.append((param_name, i))

num_genes = len(gene_space)

print(f'\n{"=" * 60}')
print('CONFIGURACIÓN DE PARÁMETROS')
print("=" * 60)
for param_name, (min_val, max_val, is_global) in parametros.items():
    tipo = "GLOBAL" if is_global else f"POR TRAMO ({n})"
    print(f'{param_name:8s} [{min_val:8.3f}, {max_val:8.3f}] → {tipo}')
print(f'\nTotal de genes: {num_genes}')
print("=" * 60 + '\n')


# ============================================================================
# DECODIFICAR SOLUCIÓN
# ============================================================================
def decodificar_solucion(solution):
    params = {
        'kaaa': [None] * n,
        'khc': [None] * n,
        'kdcs': [None] * n,
        'kdc': [None] * n,
        'khn': [None] * n,
        'kn': [None] * n,
        'ki': [None] * n,
        'khp': [None] * n,
        'kdt': [None] * n,
    }

    for gene_idx, (param_name, reach_idx) in enumerate(param_map):
        valor = solution[gene_idx]
        if reach_idx is None:
            params[param_name] = [valor] * n
        else:
            params[param_name][reach_idx] = valor

    return params


# ============================================================================
# FUNCIÓN PARA EVALUAR UNA SOLUCIÓN (SE EJECUTA EN WORKER)
# ============================================================================
def evaluar_una_solucion(solution, eval_id, filepath_original, header_dict_original, param_map_global, n_reaches):
    """
    Esta función se ejecuta en un proceso separado.
    Cada proceso crea su propio directorio temporal.
    """
    # Crear directorio temporal único
    temp_dir = tempfile.mkdtemp(prefix=f'q2k_eval_{eval_id}_')

    try:
        # Copiar archivos necesarios
        plantilla_origen = os.path.join(filepath_original, 'PlantillaBaseQ2K.xlsx')
        plantilla_destino = os.path.join(temp_dir, 'PlantillaBaseQ2K.xlsx')
        shutil.copy2(plantilla_origen, plantilla_destino)

        # Copiar otros archivos necesarios (ajusta según tus necesidades)
        for archivo in glob.glob(os.path.join(filepath_original, '*')):
            if os.path.isfile(archivo):
                nombre = os.path.basename(archivo)
                # No copiar archivos temporales
                if not any(nombre.endswith(ext) for ext in ['.out', '.txt', '.dat', '.q2k']):
                    try:
                        shutil.copy2(archivo, os.path.join(temp_dir, nombre))
                    except:
                        pass

        # Crear header_dict con directorio temporal
        header_dict_temp = header_dict_original.copy()
        header_dict_temp['filedir'] = temp_dir

        # Crear modelo
        model = Q2KModel(temp_dir, header_dict_temp)
        model.cargar_plantillas(plantilla_destino)

        # Decodificar solución (replicar la lógica aquí)
        params = {
            'kaaa': [None] * n_reaches,
            'khc': [None] * n_reaches,
            'kdcs': [None] * n_reaches,
            'kdc': [None] * n_reaches,
            'khn': [None] * n_reaches,
            'kn': [None] * n_reaches,
            'ki': [None] * n_reaches,
            'khp': [None] * n_reaches,
            'kdt': [None] * n_reaches,
        }

        for gene_idx, (param_name, reach_idx) in enumerate(param_map_global):
            valor = solution[gene_idx]
            if reach_idx is None:
                params[param_name] = [valor] * n_reaches
            else:
                params[param_name][reach_idx] = valor

        # Generar configuración
        reach_rates_custom = model.config.generar_reach_rates_custom(
            n=n_reaches,
            kaaa_list=params['kaaa'],
            khc_list=params['khc'],
            kdcs_list=params['kdcs'],
            kdc_list=params['kdc'],
            khn_list=params['khn'],
            kn_list=params['kn'],
            ki_list=params['ki'],
            khp_list=params['khp'],
            kdt_list=params['kdt']
        )

        # Ejecutar modelo
        model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera=1.06007E-06)
        model.generar_archivo_q2k()
        model.ejecutar_simulacion()
        model.analizar_resultados(generar_graficas=False)
        resultados, kge_global = model.calcular_metricas_calibracion()

        return kge_global

    except Exception as e:
        print(f'Error en evaluación {eval_id}: {e}')
        return -999

    finally:
        # Limpiar directorio temporal
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


# ============================================================================
# POOL GLOBAL DE WORKERS
# ============================================================================
pool = None
if USAR_PARALELO:
    pool = mp.Pool(processes=NUM_WORKERS)

# ============================================================================
# CONTADOR GLOBAL
# ============================================================================
if USAR_PARALELO:
    manager = mp.Manager()
    contador = manager.Value('i', 0)
    mejor_kge = manager.Value('d', -999.0)
    lock = manager.Lock()
else:
    class SimpleCounter:
        def __init__(self):
            self.value = 0


    class SimpleLock:
        def __enter__(self): return self

        def __exit__(self, *args): pass


    contador = SimpleCounter()
    mejor_kge = SimpleCounter()
    mejor_kge.value = -999.0
    lock = SimpleLock()


# ============================================================================
# FUNCIÓN FITNESS QUE USA EL POOL
# ============================================================================
def fitness_function(ga, solution, solution_idx):
    """
    Esta función SÍ se usa. PyGAD la llama para cada individuo.
    Nosotros decidimos si evaluamos en paralelo o serial.
    """
    global contador, mejor_kge, lock

    contador.value += 1
    eval_id = contador.value

    if USAR_PARALELO:
        # Evaluar usando el pool (esto reutiliza workers)
        resultado = pool.apply_async(
            evaluar_una_solucion,
            (solution, eval_id, filepath, header_dict, param_map, n)
        )
        kge = resultado.get(timeout=300)  # timeout 5 min
    else:
        # Evaluar directamente (modo serial para debug)
        kge = evaluar_una_solucion(solution, eval_id, filepath, header_dict, param_map, n)

    # Actualizar mejor KGE
    with lock:
        if kge > mejor_kge.value:
            mejor_kge.value = kge
            print(f"  *** Eval {eval_id} | NUEVO MEJOR KGE: {kge:.4f} ***")
        elif eval_id % 5 == 0:
            print(f"Eval {eval_id} | KGE: {kge:.4f}")

    return kge


# ============================================================================
# CALLBACK POR GENERACIÓN
# ============================================================================
def on_generation(ga):
    gen = ga.generations_completed
    best_solution, best_fitness, _ = ga.best_solution()
    print(f'\n{"=" * 60}')
    print(f'GENERACIÓN {gen} | Mejor KGE: {best_fitness:.4f}')
    print("=" * 60 + '\n')


# ============================================================================
# CONFIGURAR ALGORITMO GENÉTICO
# ============================================================================
ga_instance = pygad.GA(
    num_generations=50,
    num_parents_mating=4,
    fitness_func=fitness_function,  # SÍ se usa, evalúa cada individuo
    sol_per_pop=12,  # Ajusta según prefieras
    num_genes=num_genes,
    gene_space=gene_space,

    parent_selection_type="tournament",
    K_tournament=3,

    crossover_type="single_point",
    mutation_type="random",
    mutation_percent_genes=20,

    keep_elitism=1,

    on_generation=on_generation,
)

# ============================================================================
# EJECUTAR CALIBRACIÓN
# ============================================================================
print(f'\nINICIANDO CALIBRACIÓN\n')

try:
    ga_instance.run()

finally:
    # Cerrar pool al terminar
    if USAR_PARALELO and pool is not None:
        pool.close()
        pool.join()

# ============================================================================
# RESULTADOS
# ============================================================================
print('\n' + '=' * 60)
print('CALIBRACIÓN COMPLETADA')
print('=' * 60)

solution, solution_fitness, solution_idx = ga_instance.best_solution()

print(f'\nMejor KGE: {solution_fitness:.4f}')
print(f'Total de evaluaciones: {contador.value}')

print(f'\nParámetros óptimos:')
print('-' * 60)

gene_idx = 0
for param_name, (min_val, max_val, is_global) in parametros.items():
    if is_global:
        valor = solution[gene_idx]
        print(f'{param_name:8s} (global):  {valor:.4f}')
        gene_idx += 1
    else:
        print(f'{param_name:8s} (por tramo):')
        for i in range(n):
            valor = solution[gene_idx]
            print(f'  Reach {i + 1}: {valor:.4f}')
            gene_idx += 1

# ============================================================================
# SIMULACIÓN FINAL
# ============================================================================
print('\n' + '=' * 60)
print('SIMULACIÓN FINAL CON PARÁMETROS ÓPTIMOS')
print('=' * 60)

model_final = Q2KModel(filepath, header_dict)
model_final.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

params_final = decodificar_solucion(solution)

reach_rates_final = model_final.config.generar_reach_rates_custom(
    n=n,
    kaaa_list=params_final['kaaa'],
    khc_list=params_final['khc'],
    kdcs_list=params_final['kdcs'],
    kdc_list=params_final['kdc'],
    khn_list=params_final['khn'],
    kn_list=params_final['kn'],
    ki_list=params_final['ki'],
    khp_list=params_final['khp'],
    kdt_list=params_final['kdt']
)

model_final.configurar_modelo(reach_rates_custom=reach_rates_final, q_cabecera=1.06007E-06)
model_final.generar_archivo_q2k()
model_final.ejecutar_simulacion()
model_final.analizar_resultados(generar_graficas=False)
resultados_final, kge_final = model_final.calcular_metricas_calibracion()

print(f'\nKGE final verificado: {kge_final:.4f}')
print('=' * 60)