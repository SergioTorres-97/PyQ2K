from qual2k.core.model import Q2KModel
from pathlib import Path

import warnings
warnings.filterwarnings('ignore')

#Configuración
base = Path(__file__).parent.parent
filepath = f'{base}/data/templates/Chicamocha/Comprobacion'
header_dict = {
    "version": "v2.12",    "rivname": "Chicamocha",
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

model = Q2KModel(filepath, header_dict)
model.cargar_plantillas(filepath + '\\PlantillaBaseQ2K.xlsx')

n = len(model.data_reaches)
print(n)
reach_rates_custom = model.config.generar_reach_rates_custom(
    n=n,
    kaaa_list=[
        2.981884, 2.798207, 2.987273,
        2.923031, 2.655675, 2.927289,
        2.972058 # Tasa de aireación
    ],
    khc_list=[None] * n, # Hidrólisis de carbono
    kdcs_list=[None] * n, # Descomposición de carbono lento
    kdc_list=[
        1.023575, 0.348812, 1.096275,
        0.188338, 0.067997, 0.171852,
        1.080187
    ], # Descomposición de carbono rápido
    khn_list=[None] * n, # Hidrólisis de nitrógeno
    kn_list=[
        0.000427, 0.000527, 0.000332,
        0.000332, 0.000489, 0.000185,
        0.0001850
    ], # Nitrificación
    ki_list=[None] * n, # Tasa de denitrificación
    khp_list=[
        0.345786, 0.819338, 0.987707,
        0.221859, 0.337706, 0.929051,
        0.632704
    ], # Hidrólisis de fósforo
    kdt_list=[
        0.162459, 1.039082, 0.145376,
        0.802182, 0.150821, 0.050179,
        0.037982
    ] # Detritos
)
model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera= 1.053E-06)
model.config.actualizar_rates(NINpmin = 0.05, NIPpupmax = 0.001)
model.generar_archivo_q2k()
model.ejecutar_simulacion()
model.analizar_resultados(generar_graficas=True)
resultados, kge_global = model.calcular_metricas_calibracion(pesos = {
                "dissolved_oxygen": 0.3,
                "ammonium": 0.1,
                "total_phosphorus": 0.10,
                "total_kjeldahl_nitrogen": 0.1,
                "water_temp_c": 0.1,
                "carbonaceous_bod_fast": 0.3
            })

print(f'Kge: {kge_global}')