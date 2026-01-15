from qual2k.core.model import Q2KModel
from pathlib import Path

import warnings
warnings.filterwarnings('ignore')

#Configuración
base = Path(__file__).parent.parent
filepath = f'{base}/data/templates/Canal_vargas/Comprobacion'
header_dict = {
    "version": "v2.12",    "rivname": "Canal_vargas",
    "filename": "Canal_vargas",
    "filedir": filepath,
    "applabel": "Canal_vargas (6/27/2012)",
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
    # Tasa de aireación
    kaaa_list=[1.508280, 1.591000, 0.830217, 2.442002],
    khc_list=[None, None, None, None],
    kdcs_list=[None, None, None, None],
    kdc_list=[0.444736, 0.271684, 0.364008, 1.286818],
    khn_list=[None, None, None, None],
    kn_list=[0.001492, 0.000429, 0.000881, 0.000899],
    ki_list=[None, None, None, None],
    khp_list=[0.635245, 2.477876, 1.817424, 1.836482],
    kdt_list=[1.720133, 2.479366, 1.324628, 0.724895]
)

model.configurar_modelo(reach_rates_custom=reach_rates_custom, q_cabecera= 2.3148E-06)
model.generar_archivo_q2k()
model.ejecutar_simulacion()
model.analizar_resultados(generar_graficas=False)
resultados, kge_global = model.calcular_metricas_calibracion(pesos = {
                "dissolved_oxygen": 0.35,
                "ammonium": 0.15,
                "total_phosphorus": 0,
                "total_kjeldahl_nitrogen": 0,
                "water_temp_c": 0.2,
                "carbonaceous_bod_fast": 0.3
            })

print(f'Kge: {kge_global}')