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
parametros_calibrar = {
    'kaaa': (0.1, 100, True),
    'kn': (0.01, 2.0, True),
    'kdc': (0.05, 5.0, True),
}


# Crear estructura de parámetros más robusta
class ParametroConfig:
    def __init__(self):
        self.params = []
        self.gene_space = []
        self.param_names = []

    def agregar(self, nombre, lower, upper, global_flag):
        if global_flag:
            self.params.append({
                'nombre': nombre,
                'lower': lower,
                'upper': upper,
                'global': True,
                'n_genes': 1
            })
            self.gene_space.append({'low': lower, 'high': upper})
            self.param_names.append(f"{nombre}_global")
        else:
            self.params.append({
                'nombre': nombre,
                'lower': lower,
                'upper': upper,
                'global': False,
                'n_genes': n_reaches
            })
            for i in range(n_reaches):
                self.gene_space.append({'low': lower, 'high': upper})
                self.param_names.append(f"{nombre}_reach{i}")

    def decodificar_solucion(self, solution):
        """Convierte la solución en listas de parámetros"""
        if len(solution) != len(self.gene_space):
            raise ValueError(f"Solución tiene {len(solution)} genes, esperaba {len(self.gene_space)}")

        resultado = {
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

        idx = 0
        for param_info in self.params:
            nombre = param_info['nombre']

            if param_info['global']:
                # Un solo valor para todos los reaches
                valor = solution[idx]
                resultado[nombre] = [valor] * n_reaches
                idx += 1
            else:
                # Un valor por reach
                valores = solution[idx:idx + n_reaches]
                resultado[nombre] = list(valores)
                idx += n_reaches

        return resultado


# Crear configuración
config = ParametroConfig()
for param, (lower, upper, global_flag) in parametros_calibrar.items():
    config.agregar(param, lower, upper, global_flag)

n_params = len(config.gene_space)
print(f"Total de parámetros a calibrar: {n_params}")
print(f"Parámetros: {config.param_names}\n")

# =============================================================================
# VARIABLES GLOBALES PARA TRACKING
# =============================================================================
mejor_kge_global = -999
mejor_solucion_global = None
historial_fitness = []
historial_generaciones = []
contador_eval = {'n': 0}


# =============================================================================
# FUNCIÓN FITNESS
# =============================================================================
def fitness_func(ga_instance, solution, solution_idx):
    """Función fitness que PyGAD intentará MAXIMIZAR"""
    global mejor_kge_global, mejor_solucion_global

    contador_eval['n'] += 1
    eval_num = contador_eval['n']

    try:
        # VALIDACIÓN DE LA SOLUCIÓN
        if len(solution) != n_params:
            print(f"ERROR: Solución tiene {len(solution)} genes, esperaba {n_params}")
            return -999

        # Crear instancia del modelo
        model = Q2KModel(filepath, header_dict)
        model.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

        # Decodificar solución usando la clase helper
        params_dict = config.decodificar_solucion(solution)

        # Generar configuración
        reach_rates_custom = model.config.generar_reach_rates_custom(
            n=n_reaches,
            kaaa_list=params_dict['kaaa'],
            khc_list=params_dict['khc'],
            kdcs_list=params_dict['kdcs'],
            kdc_list=params_dict['kdc'],
            khn_list=params_dict['khn'],
            kn_list=params_dict['kn'],
            ki_list=params_dict['ki'],
            khp_list=params_dict['khp'],
            kdt_list=params_dict['kdt']
        )

        # Ejecutar modelo
        model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera=1.06007E-06)
        model.generar_archivo_q2k()
        model.ejecutar_simulacion()
        model.analizar_resultados()
        resultados, kge_global = model.calcular_metricas_calibracion()

        # Limpiar archivos temporales
        limpiar_archivos_temporales(filepath)

        # Validar KGE
        if np.isnan(kge_global) or np.isinf(kge_global):
            print(f"Eval {eval_num} | KGE inválido: {kge_global}")
            return -999

        # Actualizar mejor solución
        if kge_global > mejor_kge_global:
            mejor_kge_global = kge_global
            mejor_solucion_global = solution.copy()
            print(f"  *** NUEVO MEJOR KGE: {kge_global:.4f} ***")

        print(f"Eval {eval_num} | KGE: {kge_global:.4f} | Params: {[f'{p:.3f}' for p in solution]}")

        return kge_global

    except IndexError as e:
        print(f"ERROR IndexError en evaluación {eval_num}: {e}")
        print(f"  Tamaño de solution: {len(solution)}")
        print(f"  Tamaño esperado: {n_params}")
        print(f"  Solution: {solution}")
        try:
            limpiar_archivos_temporales(filepath)
        except:
            pass
        return -999

    except Exception as e:
        print(f"ERROR en evaluación {eval_num}: {type(e).__name__}: {e}")
        try:
            limpiar_archivos_temporales(filepath)
        except:
            pass
        return -999


# =============================================================================
# CALLBACK PARA TRACKING
# =============================================================================
def on_generation(ga_instance):
    """Callback ejecutado al final de cada generación"""
    generacion = ga_instance.generations_completed

    try:
        best_solution, best_fitness, _ = ga_instance.best_solution()

        historial_generaciones.append(generacion)
        historial_fitness.append(best_fitness)

        print(f"\n{'=' * 60}")
        print(f"GENERACIÓN {generacion} completada")
        print(f"Mejor KGE de esta generación: {best_fitness:.4f}")
        print(f"Mejor KGE global hasta ahora: {mejor_kge_global:.4f}")
        print(f"{'=' * 60}\n")
    except Exception as e:
        print(f"Error en callback: {e}")


# =============================================================================
# CONFIGURACIÓN DEL ALGORITMO GENÉTICO
# =============================================================================
print("\n" + "=" * 60)
print("CONFIGURACIÓN DEL ALGORITMO GENÉTICO")
print("=" * 60)

ga_instance = pygad.GA(
    num_generations=50,
    num_parents_mating=10,
    fitness_func=fitness_func,
    sol_per_pop=30,
    num_genes=n_params,
    gene_space=config.gene_space,

    parent_selection_type="tournament",
    K_tournament=3,

    crossover_type="single_point",
    crossover_probability=0.8,

    mutation_type="random",
    mutation_probability=0.15,
    mutation_percent_genes=20,

    keep_elitism=2,

    on_generation=on_generation,

    random_seed=42,
    save_best_solutions=True,
    suppress_warnings=True,

    # IMPORTANTE: Asegurar que las soluciones iniciales tengan el tamaño correcto
    initial_population=None  # PyGAD generará automáticamente
)

# Verificar que la población inicial está bien
print(f"Tamaño de población: {ga_instance.sol_per_pop}")
print(f"Número de genes por solución: {ga_instance.num_genes}")
print(f"Forma de población inicial: {ga_instance.population.shape}")
print("=" * 60 + "\n")

# =============================================================================
# EJECUTAR CALIBRACIÓN
# =============================================================================
print("INICIANDO CALIBRACIÓN")
print("=" * 60 + "\n")

try:
    ga_instance.run()
except Exception as e:
    print(f"\n!!! ERROR DURANTE LA CALIBRACIÓN: {e}")
    print("Guardando resultados parciales...\n")

# =============================================================================
# RESULTADOS FINALES
# =============================================================================
print("\n" + "=" * 60)
print("CALIBRACIÓN COMPLETADA")
print("=" * 60)

try:
    solution, solution_fitness, solution_idx = ga_instance.best_solution()

    print(f"\nMejor KGE encontrado: {solution_fitness:.4f}")
    print(f"Número total de evaluaciones: {contador_eval['n']}")
    print(f"\nParámetros óptimos:")
    for name, value in zip(config.param_names, solution):
        print(f"  {name}: {value:.4f}")

    # Gráficas
    if len(historial_fitness) > 0:
        plt.figure(figsize=(10, 5))
        plt.plot(historial_generaciones, historial_fitness, 'b-', linewidth=2, marker='o')
        plt.xlabel('Generación', fontsize=12)
        plt.ylabel('Mejor KGE', fontsize=12)
        plt.title('Evolución del Mejor KGE', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{filepath}/calibracion_ga_resultados.png', dpi=300, bbox_inches='tight')
        print(f"\nGráfica guardada en: {filepath}/calibracion_ga_resultados.png")

    # Simulación final
    print("\n" + "=" * 60)
    print("SIMULACIÓN FINAL CON PARÁMETROS ÓPTIMOS")
    print("=" * 60)

    model_final = Q2KModel(filepath, header_dict)
    model_final.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

    params_dict_final = config.decodificar_solucion(solution)

    reach_rates_opt = model_final.config.generar_reach_rates_custom(
        n=n_reaches,
        kaaa_list=params_dict_final['kaaa'],
        khc_list=params_dict_final['khc'],
        kdcs_list=params_dict_final['kdcs'],
        kdc_list=params_dict_final['kdc'],
        khn_list=params_dict_final['khn'],
        kn_list=params_dict_final['kn'],
        ki_list=params_dict_final['ki'],
        khp_list=params_dict_final['khp'],
        kdt_list=params_dict_final['kdt']
    )

    model_final.configurar_modelo(reach_rates_custom=reach_rates_opt, q_cabecera=1.06007E-06)
    model_final.generar_archivo_q2k()
    model_final.ejecutar_simulacion()
    model_final.analizar_resultados(generar_graficas=False)
    resultados_final, kge_final = model_final.calcular_metricas_calibracion()

    print(f"\nKGE final verificado: {kge_final:.4f}")
    print("=" * 60)

    # Guardar resultados
    with open(f'{filepath}/parametros_calibrados.txt', 'w') as f:
        f.write("RESULTADOS DE CALIBRACIÓN - ALGORITMO GENÉTICO\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"KGE Final: {kge_final:.4f}\n")
        f.write(f"Evaluaciones totales: {contador_eval['n']}\n\n")
        f.write("Parámetros óptimos:\n")
        for name, value in zip(config.param_names, solution):
            f.write(f"  {name}: {value:.4f}\n")

    print(f"\nResultados guardados en: {filepath}/parametros_calibrados.txt")

except Exception as e:
    print(f"Error al procesar resultados finales: {e}")