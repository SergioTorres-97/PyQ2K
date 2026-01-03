from pathlib import Path
import multiprocessing as mp
from qual2k.core.calibrator import Calibracion

mp.freeze_support()

# Configuración base
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

# Parámetros a calibrar
parametros = {
    'kaaa': (0.1, 3, False),
    'kn': (0.0005, 0.05, False),
    'kdc': (0.05, 1.5, False),
    'kdt': (0.05, 2.5, False),
}

# ========================================================================
# OPCIÓN 1: Configuración manual completa
# ========================================================================
calibracion = Calibracion(
    filepath=filepath,
    header_dict=header_dict,
    parametros=parametros,
    # Básicos
    num_generations=200,
    population_size=80,
    num_parents_mating=32,
    # Selección
    parent_selection_type="tournament",
    k_tournament=3,
    # Cruce
    crossover_type="single_point",
    crossover_probability=0.9,
    # Mutación
    mutation_type="random",
    mutation_probability=0.15,
    mutation_percent_genes=20,
    # Elitismo
    keep_elitism=5,
    # Reproducibilidad
    random_seed=42,
    # Paralelismo
    num_workers=4,
    usar_paralelo=True
)

# ========================================================================
# OPCIÓN 2: Usar preset
# ========================================================================
# preset_config = CalibracionPresets.balanceado()
# calibracion = Calibracion(
#     filepath=filepath,
#     header_dict=header_dict,
#     parametros=parametros,
#     **preset_config
# )

# ========================================================================
# OPCIÓN 3: Configuración avanzada con criterios de parada
# ========================================================================
# calibracion = Calibracion(
#     filepath=filepath,
#     header_dict=header_dict,
#     parametros=parametros,
#     num_generations=200,
#     population_size=50,
#     num_parents_mating=20,
#     parent_selection_type="rank",
#     crossover_type="two_points",
#     mutation_type="adaptive",
#     stop_criteria=["reach_0.95", "saturate_50"],  # Para si alcanza KGE=0.95 o se estanca 50 gens
#     random_seed=42
# )

# Exportar configuración antes de ejecutar
calibracion.exportar_configuracion()

# Ejecutar calibración
resultado = calibracion.ejecutar()

# Obtener parámetros calibrados y historial
if resultado is not None:
    solucion, kge = resultado
    params_dict = calibracion.get_parametros_calibrados()
    historial = calibracion.get_historial()

    print(f"\nParámetros calibrados disponibles: {params_dict.keys()}")
    print(f"Total de generaciones: {len(historial)}")
