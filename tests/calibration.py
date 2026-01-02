from qual2k.core.model import Q2KModel
from pathlib import Path
import pygad
import warnings
import os
import glob

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
# FUNCIÓN PARA LIMPIAR ARCHIVOS
# ============================================================================
def limpiar_archivos():
    for ext in ['*.out', '*.txt', '*.dat', '*.q2k']:
        for archivo in glob.glob(os.path.join(filepath, ext)):
            try:
                os.remove(archivo)
            except:
                pass


# ============================================================================
# PARÁMETROS A CALIBRAR
# ============================================================================
# Solo 3 parámetros para empezar simple
parametros = {
    'kaaa': (0.1, 100),  # Tasa de aireación
    'kn': (0.01, 2.0),  # Nitrificación
    'kdc': (0.05, 5.0),  # Descomposición carbono rápido
}

num_params = len(parametros)
print(f'Parámetros a calibrar: {list(parametros.keys())}')


# ============================================================================
# FUNCIÓN FITNESS
# ============================================================================
def fitness_function(ga, solution, solution_idx):
    """
    solution[0] = kaaa
    solution[1] = kn
    solution[2] = kdc
    """
    try:
        # Crear modelo
        model = Q2KModel(filepath, header_dict)
        model.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

        # Asignar parámetros de la solución
        kaaa_val = solution[0]
        kn_val = solution[1]
        kdc_val = solution[2]

        # Generar configuración
        reach_rates_custom = model.config.generar_reach_rates_custom(
            n=n,
            kaaa_list=[kaaa_val] * n,  # mismo valor para todos los reaches
            khc_list=[None] * n,
            kdcs_list=[None] * n,
            kdc_list=[kdc_val] * n,  # mismo valor para todos los reaches
            khn_list=[None] * n,
            kn_list=[kn_val] * n,  # mismo valor para todos los reaches
            ki_list=[None] * n,
            khp_list=[None] * n,
            kdt_list=[None] * n
        )

        # Ejecutar modelo
        model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera=1.06007E-06)
        model.generar_archivo_q2k()
        model.ejecutar_simulacion()
        model.analizar_resultados(generar_graficas=False)
        resultados, kge_global = model.calcular_metricas_calibracion()

        # Limpiar archivos
        limpiar_archivos()

        # Imprimir progreso
        print(f'KGE: {kge_global:.4f} | kaaa: {kaaa_val:.2f}, kn: {kn_val:.3f}, kdc: {kdc_val:.2f}')

        return kge_global  # PyGAD maximiza esto

    except Exception as e:
        print(f'Error: {e}')
        limpiar_archivos()
        return -999  # Penalización


# ============================================================================
# CONFIGURAR ALGORITMO GENÉTICO
# ============================================================================
ga_instance = pygad.GA(
    num_generations=30,  # Número de generaciones
    num_parents_mating=4,  # Padres para cruce
    fitness_func=fitness_function,
    sol_per_pop=10,  # Tamaño de población
    num_genes=num_params,  # 3 genes (kaaa, kn, kdc)

    # Rangos de cada parámetro
    gene_space=[
        {'low': 0.1, 'high': 3},  # kaaa
        {'low': 0.001, 'high': 0.5},  # kn
        {'low': 0.1, 'high': 1.5},  # kdc
    ],

    parent_selection_type="tournament",
    K_tournament=3,

    crossover_type="single_point",
    mutation_type="random",
    mutation_percent_genes=20,

    keep_elitism=1,
)

# ============================================================================
# EJECUTAR CALIBRACIÓN
# ============================================================================
print('\n' + '=' * 60)
print('INICIANDO CALIBRACIÓN')
print('=' * 60 + '\n')

ga_instance.run()

# ============================================================================
# RESULTADOS
# ============================================================================
print('\n' + '=' * 60)
print('CALIBRACIÓN COMPLETADA')
print('=' * 60)

solution, solution_fitness, solution_idx = ga_instance.best_solution()

print(f'\nMejor KGE: {solution_fitness:.4f}')
print(f'\nParámetros óptimos:')
print(f'  kaaa: {solution[0]:.4f}')
print(f'  kn: {solution[1]:.4f}')
print(f'  kdc: {solution[2]:.4f}')

# ============================================================================
# SIMULACIÓN FINAL CON PARÁMETROS ÓPTIMOS
# ============================================================================
print('\n' + '=' * 60)
print('SIMULACIÓN FINAL')
print('=' * 60)

model_final = Q2KModel(filepath, header_dict)
model_final.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

reach_rates_final = model_final.config.generar_reach_rates_custom(
    n=n,
    kaaa_list=[solution[0]] * n,
    khc_list=[None] * n,
    kdcs_list=[None] * n,
    kdc_list=[solution[2]] * n,
    khn_list=[None] * n,
    kn_list=[solution[1]] * n,
    ki_list=[None] * n,
    khp_list=[None] * n,
    kdt_list=[None] * n
)

model_final.configurar_modelo(reach_rates_custom=reach_rates_final, q_cabecera=1.06007E-06)
model_final.generar_archivo_q2k()
model_final.ejecutar_simulacion()
model_final.analizar_resultados(generar_graficas=False)
resultados_final, kge_final = model_final.calcular_metricas_calibracion()

print(f'\nKGE final verificado: {kge_final:.4f}')