from pathlib import Path
import multiprocessing as mp

from qual2k.core.calibrator import Calibracion

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
base = Path(__file__).parent.parent

HEADER_BASE = {
    "version":      "v2.12",
    "xmon":         6,
    "xday":         27,
    "xyear":        2012,
    "timezonehour": -6,
    "pco2":         0.000347,
    "dtuser":       4.16666666666667E-03,
    "tf":           5,
    "IMeth":        "Euler",
    "IMethpH":      "Brent",
}

config_tramo3s = {
    'filepath':    str(base / 'data/templates/Tramo_3s'),
    'header_dict': {**HEADER_BASE,
                    "rivname":  "Tramo_3s",
                    "filename": "Tramo_3s",
                    "filedir":  str(base / 'data/templates/Tramo_3s'),
                    "applabel": "Tramo_3s (6/27/2012)"},
    'q_cabecera':  4.1666E-06,
}

parametros_tramo3s = {
    'kaaa': (0.5, 3.0, False),
    'kdc':  (0.1, 2.0, False),
    'kn':   (0.1, 1.0, False),
    'khp':  (0.1, 2.0, False),
    'kdt':  (0.01, 1.5, False),
}

# ============================================================================
# CALIBRACIÓN
# ============================================================================

def main():
    calibrador = Calibracion(
        filepath=config_tramo3s['filepath'],
        header_dict=config_tramo3s['header_dict'],
        parametros=parametros_tramo3s,
        q_cabecera=config_tramo3s['q_cabecera'],
        rates_overrides={
            'kpath': 0.05,
            'aPath': 0.001,
        },

        num_generations=20,
        population_size=30,
        num_parents_mating=15,

        parent_selection_type="tournament",
        k_tournament=3,

        crossover_type="uniform",
        crossover_probability=0.85,

        mutation_type="adaptive",
        mutation_probability=[0.35, 0.08],
        mutation_percent_genes=20,

        keep_elitism=5,
        stop_criteria="saturate_5",

        random_seed=42,
        usar_paralelo=True,
        num_workers=max(1, mp.cpu_count() - 1),
    )

    resultado = calibrador.ejecutar(generar_graficas=True)

    if resultado is not None:
        solucion, kge = resultado
        print(f"\nKGE Tramo 3S: {kge:.6f}")


if __name__ == '__main__':
    mp.freeze_support()
    main()
