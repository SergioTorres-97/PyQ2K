from qual2k.core.model import Q2KModel
from pathlib import Path
import pygad
import warnings
import os
import glob
import shutil
import tempfile
import multiprocessing as mp

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACIÓN BASE (FUERA DE __main__)
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

# ============================================================================
# PARÁMETROS A CALIBRAR (FUERA DE __main__)
# ============================================================================
parametros = {
    'kaaa': (0.1, 3, False),
    'kn': (0.0005, 0.05, False),
    'kdc': (0.05, 1.5, False),
    'kdt': (0.05, 2.5, False),
}


# ============================================================================
# FUNCIONES AUXILIARES (FUERA DE __main__)
# ============================================================================
def decodificar_solucion(solution, param_map_arg, n_reaches):
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

    for gene_idx, (param_name, reach_idx) in enumerate(param_map_arg):
        valor = solution[gene_idx]
        if reach_idx is None:
            params[param_name] = [valor] * n_reaches
        else:
            params[param_name][reach_idx] = valor

    return params


def evaluar_una_solucion(args):
    solution, eval_id, filepath_original, header_dict_original, param_map_arg, n_reaches = args

    temp_dir = tempfile.mkdtemp(prefix=f'q2k_eval_{eval_id}_')

    try:
        plantilla_origen = os.path.join(filepath_original, 'PlantillaBaseQ2K.xlsx')
        plantilla_destino = os.path.join(temp_dir, 'PlantillaBaseQ2K.xlsx')
        shutil.copy2(plantilla_origen, plantilla_destino)

        for archivo in glob.glob(os.path.join(filepath_original, '*')):
            if os.path.isfile(archivo):
                nombre = os.path.basename(archivo)
                if not any(nombre.endswith(ext) for ext in ['.out', '.txt', '.dat', '.q2k']):
                    try:
                        shutil.copy2(archivo, os.path.join(temp_dir, nombre))
                    except:
                        pass

        header_dict_temp = header_dict_original.copy()
        header_dict_temp['filedir'] = temp_dir

        model = Q2KModel(temp_dir, header_dict_temp)
        model.cargar_plantillas(plantilla_destino)

        params = decodificar_solucion(solution, param_map_arg, n_reaches)

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

        model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera=1.06007E-06)
        model.generar_archivo_q2k()
        model.ejecutar_simulacion()
        model.analizar_resultados(generar_graficas=False)
        resultados, kge_global = model.calcular_metricas_calibracion()

        return (eval_id, kge_global)

    except Exception as e:
        print(f'Error en evaluación {eval_id}: {e}')
        return (eval_id, -999)

    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


# ============================================================================
# PROGRAMA PRINCIPAL
# ============================================================================
if __name__ == '__main__':
    mp.freeze_support()

    print('\n' + '=' * 60)
    print('CALIBRACIÓN AUTOMÁTICA DE QUAL2K CON ALGORITMO GENÉTICO')
    print('=' * 60)

    model_temp = Q2KModel(filepath, header_dict)
    model_temp.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')
    n = len(model_temp.data_reaches)
    print(f'\nNúmero de reaches: {n}')

    NUM_WORKERS = min(4, mp.cpu_count() - 1)
    USAR_PARALELO = True

    print(f'Modo: {"PARALELO" if USAR_PARALELO else "SERIAL"}')
    if USAR_PARALELO:
        print(f'Workers: {NUM_WORKERS}')

    # Crear gene_space y mapeo
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
        tipo = "GLOBAL (1 valor)" if is_global else f"POR TRAMO ({n} valores)"
        print(f'{param_name:8s} [{min_val:8.3f}, {max_val:8.3f}] → {tipo}')
    print(f'\nTotal de genes a calibrar: {num_genes}')
    print("=" * 60)

    # Pool de workers
    pool = None
    if USAR_PARALELO:
        pool = mp.Pool(processes=NUM_WORKERS)
        print(f'\nPool de {NUM_WORKERS} workers creado')

    # Contadores
    contador = {'value': 0}
    mejor_kge = {'value': -999.0}


    # Función fitness
    def fitness_function(ga, solution, solution_idx):
        contador['value'] += 1
        eval_id = contador['value']

        if USAR_PARALELO and pool is not None:
            args = (solution, eval_id, filepath, header_dict, param_map, n)
            resultado = pool.apply_async(evaluar_una_solucion, (args,))
            eval_id_result, kge = resultado.get(timeout=300)
        else:
            args = (solution, eval_id, filepath, header_dict, param_map, n)
            eval_id_result, kge = evaluar_una_solucion(args)

        if kge > mejor_kge['value']:
            mejor_kge['value'] = kge
            print(f"  *** Eval {eval_id} | NUEVO MEJOR KGE: {kge:.4f} ***")
        elif eval_id % 5 == 0:
            print(f"Eval {eval_id} | KGE: {kge:.4f}")

        return kge


    # Callback
    def on_generation(ga):
        gen = ga.generations_completed
        best_solution, best_fitness, _ = ga.best_solution()
        print(f'\n{"=" * 60}')
        print(f'GENERACIÓN {gen} COMPLETADA')
        print(f'Mejor KGE de esta generación: {best_fitness:.4f}')
        print(f'Mejor KGE global: {mejor_kge["value"]:.4f}')
        print("=" * 60 + '\n')


    # Configurar GA
    print('\n' + '=' * 60)
    print('CONFIGURACIÓN DEL ALGORITMO GENÉTICO')
    print('=' * 60)

    NUM_GENERATIONS = 100
    POPULATION_SIZE = 40
    NUM_PARENTS_MATING = 16

    print(f'Generaciones: {NUM_GENERATIONS}')
    print(f'Tamaño de población: {POPULATION_SIZE}')
    print(f'Padres para cruce: {NUM_PARENTS_MATING}')
    print('=' * 60)

    ga_instance = pygad.GA(
        num_generations=NUM_GENERATIONS,
        num_parents_mating=NUM_PARENTS_MATING,
        fitness_func=fitness_function,
        sol_per_pop=POPULATION_SIZE,
        num_genes=num_genes,
        gene_space=gene_space,

        parent_selection_type="tournament",
        K_tournament=3,

        crossover_type="single_point",
        crossover_probability=0.9,

        mutation_type="random",
        mutation_probability=0.2,
        mutation_percent_genes=20,

        keep_elitism=3,

        on_generation=on_generation,
    )

    # Ejecutar calibración
    print(f'\n{"=" * 60}')
    print('INICIANDO CALIBRACIÓN')
    print('=' * 60 + '\n')

    try:
        ga_instance.run()

        # ====================================================================
        # OBTENER MEJOR SOLUCIÓN (ANTES DE CERRAR EL POOL)
        # ====================================================================
        print('\n' + '=' * 60)
        print('CALIBRACIÓN COMPLETADA')
        print('=' * 60)

        solution, solution_fitness, solution_idx = ga_instance.best_solution()

        print(f'\nMejor KGE encontrado: {solution_fitness:.4f}')
        print(f'Total de evaluaciones: {contador["value"]}')

        print(f'\n{"=" * 60}')
        print('PARÁMETROS ÓPTIMOS')
        print('=' * 60)

        gene_idx = 0
        for param_name, (min_val, max_val, is_global) in parametros.items():
            if is_global:
                valor = solution[gene_idx]
                print(f'{param_name:8s} (global):  {valor:.6f}')
                gene_idx += 1
            else:
                print(f'{param_name:8s} (por tramo):')
                for i in range(n):
                    valor = solution[gene_idx]
                    print(f'  Reach {i + 1}: {valor:.6f}')
                    gene_idx += 1

        print('=' * 60)

    except KeyboardInterrupt:
        print('\n\n¡CALIBRACIÓN INTERRUMPIDA POR USUARIO!\n')
        solution = None

    finally:
        # CERRAR POOL AL FINAL
        if USAR_PARALELO and pool is not None:
            print('\nCerrando pool de workers...')
            pool.close()
            pool.join()
            print('Pool cerrado correctamente')

    # ========================================================================
    # SIMULACIÓN FINAL (SOLO SI TENEMOS SOLUCIÓN)
    # ========================================================================
    if solution is not None:
        print('\n' + '=' * 60)
        print('SIMULACIÓN FINAL CON PARÁMETROS ÓPTIMOS')
        print('=' * 60)

        model_final = Q2KModel(filepath, header_dict)
        model_final.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

        params_final = decodificar_solucion(solution, param_map, n)

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
        model_final.analizar_resultados(generar_graficas=True)
        resultados_final, kge_final = model_final.calcular_metricas_calibracion()

        print(f'\nKGE final verificado: {kge_final:.4f}')

        # Guardar resultados
        output_file = os.path.join(filepath, 'parametros_calibrados.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('=' * 60 + '\n')
            f.write('RESULTADOS DE CALIBRACIÓN - ALGORITMO GENÉTICO\n')
            f.write('=' * 60 + '\n\n')
            f.write(f'KGE Final: {kge_final:.6f}\n')
            f.write(f'Total de evaluaciones: {contador["value"]}\n')
            f.write(f'Generaciones: {NUM_GENERATIONS}\n')
            f.write(f'Tamaño de población: {POPULATION_SIZE}\n\n')
            f.write('PARÁMETROS ÓPTIMOS:\n')
            f.write('-' * 60 + '\n')

            gene_idx = 0
            for param_name, (min_val, max_val, is_global) in parametros.items():
                if is_global:
                    valor = solution[gene_idx]
                    f.write(f'{param_name:8s} (global):  {valor:.6f}\n')
                    gene_idx += 1
                else:
                    f.write(f'{param_name:8s} (por tramo):\n')
                    for i in range(n):
                        valor = solution[gene_idx]
                        f.write(f'  Reach {i + 1}: {valor:.6f}\n')
                        gene_idx += 1

        print(f'\nResultados guardados en: {output_file}')

    print('\n' + '=' * 60)
    print('PROCESO FINALIZADO')
    print('=' * 60 + '\n')