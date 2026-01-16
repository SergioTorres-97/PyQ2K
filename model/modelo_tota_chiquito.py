from qual2k.core.model import Q2KModel
from pathlib import Path

import warnings
warnings.filterwarnings('ignore')

#Configuración
base = Path(__file__).parent.parent
filepath = f'{base}/data/templates/Tramo_3s/Comprobacion'
header_dict = {
    "version": "v2.12",    "rivname": "Tramo_3s",
    "filename": "Tramo_3s",
    "filedir": filepath,
    "applabel": "Tramo_3s (6/27/2012)",
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

model = Q2KModel(filepath, header_dict)
model.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

n = len(model.data_reaches)
print(n)
reach_rates_custom = model.config.generar_reach_rates_custom(
    n=n,
    kaaa_list=[2.658071, 2.825499, 2.832378, 2.146497, 2.966648],  # Tasa de aireación
    khc_list=[None] * n,  # Hidrólisis de carbono
    kdcs_list=[None] * n,  # Descomposición de carbono lento
    kdc_list=[0.978387, 0.202544, 0.247739, 0.437239, 1.027858],  # Descomposición de carbono rápido
    khn_list=[None] * n,  # Hidrólisis de nitrógeno
    kn_list=[0.002423, 0.002863, 0.000685, 0.008027, 0.038977],  # Nitrificación
    ki_list=[None] * n,  # Tasa de denitricación
    khp_list=[0.796154, 0.592190, 0.088888, 1.512231, 1.696425],  # Hidrólisis de fósforo
    kdt_list=[0.679611, 2.123592, 0.134252, 1.079767, 1.279208]  # Detritos
)

model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera= 1.053E-06)
model.generar_archivo_q2k()
model.ejecutar_simulacion()
model.analizar_resultados(generar_graficas=True)
resultados, kge_global = model.calcular_metricas_calibracion(pesos = {
                "water_temp_c": 0.05,
                "conductivity": 0.05,
                "nitrate": 0.05,
                "pathogen": 0.10,
                "pH": 0.05,
                "total_suspended_solids": 0.05,
                "dissolved_oxygen": 0.30,
                "carbonaceous_bod_fast": 0.30,
                "total_kjeldahl_nitrogen": 0.02,
                "ammonium": 0.02,
                "total_phosphorus": 0.01
            })

print(f'Kge: {kge_global}')