from qual2k.core.model import Q2KModel
from pathlib import Path
import numpy as np
import pygad
import warnings
import os
import glob
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

# Configuración base
base_path = Path(__file__).parent.parent
filepath = f'{base_path}/data/templates/Chicamocha'
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


# Función para limpiar archivos temporales
def limpiar_archivos_temporales(directorio):
    """Elimina archivos temporales generados por Q2K"""
    extensiones = ['*.out', '*.txt', '*.dat', '*.q2k']
    archivos_eliminados = 0

    for ext in extensiones:
        patron = os.path.join(directorio, ext)
        archivos = glob.glob(patron)
        for archivo in archivos:
            try:
                os.remove(archivo)
                archivos_eliminados += 1
            except Exception as e:
                pass
    return archivos_eliminados


# Limpiar archivos iniciales
print("Limpiando archivos temporales iniciales...")
limpiar_archivos_temporales(filepath)

# Número de reaches
model_temp = Q2KModel(filepath, header_dict)
model_temp.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')
n_reaches = len(model_temp.data_reaches)
print(f"Número de reaches: {n_reaches}")

# =============================================================================
# CONFIGURACIÓN DE PARÁMETROS A CALIBRAR
# =============================================================================
# Estructura: {nombre: (min, max, aplicar_global)}
# True = un valor para todos los reaches
# False = un valor diferente por reach
parametros_calibrar = {
    'kaaa': (0.1, 3, True),
    # 'kn': (0.01, 2.0, True),
    # 'kdc': (0.05, 5.0, True),
    # 'khc': (0.001, 0.5, True),
    'kdcs': (0.1, 1, True),
    'khn': (0.001, 0.5, True),
    # 'ki': (0.001, 0.5, True),
    # 'khp': (0.001, 0.5, True),
    'kdt': (0.2, 3, True),
}

# Crear límites y nombres
gene_space = []
param_names = []

for param, (lower, upper, todos) in parametros_calibrar.items():
    if todos:
        gene_space.append({'low': lower, 'high': upper})
        param_names.append(f"{param}_global")
    else:
        for i in range(n_reaches):
            gene_space.append({'low': lower, 'high': upper})
            param_names.append(f"{param}_reach{i}")

n_params = len(gene_space)
print(f"Total de parámetros a calibrar: {n_params}")
print(f"Parámetros: {param_names}\n")

# =============================================================================
# VARIABLES GLOBALES PARA TRACKING
# =============================================================================
mejor_kge_global = -999
mejor_solucion_global = None
historial_fitness = []
historial_generaciones = []
contador_eval = {'n': 0}


# =============================================================================
# FUNCIÓN FITNESS (la que maximiza PyGAD)
# =============================================================================
def fitness_func(ga_instance, solution, solution_idx):
    """
    Función fitness que PyGAD intentará MAXIMIZAR
    Retorna el KGE directamente (valores más altos = mejor)
    """
    global mejor_kge_global, mejor_solucion_global

    contador_eval['n'] += 1
    eval_num = contador_eval['n']

    try:
        # Crear instancia del modelo
        model = Q2KModel(filepath, header_dict)
        model.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

        # Mapear parámetros de la solución
        idx = 0
        kaaa_list = []
        khc_list = []
        kdcs_list = []
        kdc_list = []
        khn_list = []
        kn_list = []
        ki_list = []
        khp_list = []
        kdt_list = []

        for param, (_, _, todos) in parametros_calibrar.items():
            if todos:
                valor = solution[idx]
                idx += 1
                if param == 'kaaa':
                    kaaa_list = [valor] * n_reaches
                elif param == 'khc':
                    khc_list = [valor] * n_reaches
                elif param == 'kdcs':
                    kdcs_list = [valor] * n_reaches
                elif param == 'kdc':
                    kdc_list = [valor] * n_reaches
                elif param == 'khn':
                    khn_list = [valor] * n_reaches
                elif param == 'kn':
                    kn_list = [valor] * n_reaches
                elif param == 'ki':
                    ki_list = [valor] * n_reaches
                elif param == 'khp':
                    khp_list = [valor] * n_reaches
                elif param == 'kdt':
                    kdt_list = [valor] * n_reaches

        # Generar configuración
        reach_rates_custom = model.config.generar_reach_rates_custom(
            n=n_reaches,
            kaaa_list=kaaa_list if kaaa_list else [None] * n_reaches,
            khc_list=khc_list if khc_list else [None] * n_reaches,
            kdcs_list=kdcs_list if kdcs_list else [None] * n_reaches,
            kdc_list=kdc_list if kdc_list else [None] * n_reaches,
            khn_list=khn_list if khn_list else [None] * n_reaches,
            kn_list=kn_list if kn_list else [None] * n_reaches,
            ki_list=ki_list if ki_list else [None] * n_reaches,
            khp_list=khp_list if khp_list else [None] * n_reaches,
            kdt_list=kdt_list if kdt_list else [None] * n_reaches
        )

        # Ejecutar modelo
        model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera=1.06007E-06)
        model.generar_archivo_q2k()
        model.ejecutar_simulacion()
        model.analizar_resultados()
        resultados, kge_global = model.calcular_metricas_calibracion()

        # Limpiar archivos temporales
        limpiar_archivos_temporales(filepath)

        # Actualizar mejor solución
        if kge_global > mejor_kge_global:
            mejor_kge_global = kge_global
            mejor_solucion_global = solution.copy()
            print(f"  *** NUEVO MEJOR KGE: {kge_global:.4f} ***")

        fitness = kge_global  # PyGAD MAXIMIZA, así que retornamos KGE directo

        print(f"Eval {eval_num} | KGE: {kge_global:.4f} | Params: {[f'{p:.3f}' for p in solution]}")

        return fitness

    except Exception as e:
        print(f"Error en evaluación {eval_num}: {e}")
        try:
            limpiar_archivos_temporales(filepath)
        except:
            pass
        return -999  # Penalización


# =============================================================================
# CALLBACK PARA TRACKING DE GENERACIONES
# =============================================================================
def on_generation(ga_instance):
    """Callback ejecutado al final de cada generación"""
    generacion = ga_instance.generations_completed

    # Obtener mejor fitness de la generación actual
    best_solution, best_fitness, _ = ga_instance.best_solution()

    historial_generaciones.append(generacion)
    historial_fitness.append(best_fitness)

    print(f"\n{'=' * 60}")
    print(f"GENERACIÓN {generacion} completada")
    print(f"Mejor KGE de esta generación: {best_fitness:.4f}")
    print(f"Mejor KGE global hasta ahora: {mejor_kge_global:.4f}")
    print(f"{'=' * 60}\n")


# =============================================================================
# CONFIGURACIÓN DEL ALGORITMO GENÉTICO CON PyGAD
# =============================================================================
print("\n" + "=" * 60)
print("CONFIGURACIÓN DEL ALGORITMO GENÉTICO")
print("=" * 60)

ga_instance = pygad.GA(
    num_generations=50,  # Número de generaciones
    num_parents_mating=10,  # Número de padres para cruce
    fitness_func=fitness_func,  # Función fitness
    sol_per_pop=30,  # Tamaño de población
    num_genes=n_params,  # Número de genes (parámetros)
    gene_space=gene_space,  # Espacio de búsqueda

    # Tipo de selección
    parent_selection_type="tournament",  # Opciones: sss, rws, sus, rank, random, tournament
    K_tournament=3,  # Tamaño del torneo

    # Tipo de cruce
    crossover_type="single_point",  # Opciones: single_point, two_points, uniform, scattered
    crossover_probability=0.8,  # Probabilidad de cruce

    # Tipo de mutación
    mutation_type="random",  # Opciones: random, swap, inversion, scramble, adaptive
    mutation_probability=0.15,  # Probabilidad de mutación
    mutation_percent_genes=20,  # Porcentaje de genes a mutar

    # Elitismo
    keep_elitism=2,  # Número de mejores soluciones a preservar

    # Callbacks
    on_generation=on_generation,  # Función a ejecutar cada generación

    # Otros
    random_seed=42,
    save_best_solutions=True,  # Guardar mejores soluciones
    suppress_warnings=True
)

# =============================================================================
# EJECUTAR CALIBRACIÓN
# =============================================================================
print("\n" + "=" * 60)
print("INICIANDO CALIBRACIÓN CON ALGORITMO GENÉTICO")
print("=" * 60)
print(f"Población: {ga_instance.sol_per_pop}")
print(f"Generaciones: {ga_instance.num_generations}")
print(f"Parámetros a calibrar: {n_params}")
print(f"Directorio: {filepath}")
print("=" * 60 + "\n")

# Ejecutar el algoritmo genético
ga_instance.run()

# =============================================================================
# RESULTADOS FINALES
# =============================================================================
print("\n" + "=" * 60)
print("CALIBRACIÓN COMPLETADA")
print("=" * 60)

# Mejor solución encontrada
solution, solution_fitness, solution_idx = ga_instance.best_solution()

print(f"\nMejor KGE encontrado: {solution_fitness:.4f}")
print(f"Número total de evaluaciones: {contador_eval['n']}")
print(f"\nParámetros óptimos:")
for name, value in zip(param_names, solution):
    print(f"  {name}: {value:.4f}")

# =============================================================================
# GRÁFICA DE EVOLUCIÓN
# =============================================================================
plt.figure(figsize=(12, 6))

plt.subplot(1, 2, 1)
plt.plot(historial_generaciones, historial_fitness, 'b-', linewidth=2)
plt.xlabel('Generación', fontsize=12)
plt.ylabel('Mejor KGE', fontsize=12)
plt.title('Evolución del Mejor KGE por Generación', fontsize=14)
plt.grid(True, alpha=0.3)

plt.subplot(1, 2, 2)
ga_instance.plot_fitness()

plt.tight_layout()
plt.savefig(f'{filepath}/calibracion_ga_resultados.png', dpi=300, bbox_inches='tight')
print(f"\nGráfica guardada en: {filepath}/calibracion_ga_resultados.png")

# =============================================================================
# SIMULACIÓN FINAL CON PARÁMETROS ÓPTIMOS
# =============================================================================
print("\n" + "=" * 60)
print("SIMULACIÓN FINAL CON PARÁMETROS ÓPTIMOS")
print("=" * 60)

model_final = Q2KModel(filepath, header_dict)
model_final.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

# Reconstruir parámetros óptimos
idx = 0
kaaa_opt = []
khc_opt = []
kdcs_opt = []
kdc_opt = []
khn_opt = []
kn_opt = []
ki_opt = []
khp_opt = []
kdt_opt = []

for param, (_, _, todos) in parametros_calibrar.items():
    if todos:
        valor = solution[idx]
        idx += 1
        if param == 'kaaa':
            kaaa_opt = [valor] * n_reaches
        elif param == 'khc':
            khc_opt = [valor] * n_reaches
        elif param == 'kdcs':
            kdcs_opt = [valor] * n_reaches
        elif param == 'kdc':
            kdc_opt = [valor] * n_reaches
        elif param == 'khn':
            khn_opt = [valor] * n_reaches
        elif param == 'kn':
            kn_opt = [valor] * n_reaches
        elif param == 'ki':
            ki_opt = [valor] * n_reaches
        elif param == 'khp':
            khp_opt = [valor] * n_reaches
        elif param == 'kdt':
            kdt_opt = [valor] * n_reaches

reach_rates_opt = model_final.config.generar_reach_rates_custom(
    n=n_reaches,
    kaaa_list=kaaa_opt if kaaa_opt else [None] * n_reaches,
    khc_list=khc_opt if khc_opt else [None] * n_reaches,
    kdcs_list=kdcs_opt if kdcs_opt else [None] * n_reaches,
    kdc_list=kdc_opt if kdc_opt else [None] * n_reaches,
    khn_list=khn_opt if khn_opt else [None] * n_reaches,
    kn_list=kn_opt if kn_opt else [None] * n_reaches,
    ki_list=ki_opt if ki_opt else [None] * n_reaches,
    khp_list=khp_opt if khp_opt else [None] * n_reaches,
    kdt_list=kdt_opt if kdt_opt else [None] * n_reaches
)

model_final.configurar_modelo(reach_rates_custom=reach_rates_opt, q_cabecera=1.06007E-06)
model_final.generar_archivo_q2k()
model_final.ejecutar_simulacion()
model_final.analizar_resultados()
resultados_final, kge_final = model_final.calcular_metricas_calibracion()

print(f"\nKGE final verificado: {kge_final:.4f}")
print("=" * 60)

# Guardar resultados
print("\nGuardando resultados de calibración...")
with open(f'{filepath}/parametros_calibrados.txt', 'w') as f:
    f.write("RESULTADOS DE CALIBRACIÓN - ALGORITMO GENÉTICO\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"KGE Final: {kge_final:.4f}\n")
    f.write(f"Evaluaciones totales: {contador_eval['n']}\n\n")
    f.write("Parámetros óptimos:\n")
    for name, value in zip(param_names, solution):
        f.write(f"  {name}: {value:.4f}\n")

print(f"Resultados guardados en: {filepath}/parametros_calibrados.txt")