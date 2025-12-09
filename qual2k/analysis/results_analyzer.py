import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List, Tuple
from qual2k.analysis import metricas

class Q2KResultsAnalyzer:
    """
    Analiza los resultados de las simulaciones QUAL2K.
    """

    @staticmethod
    def leer_secciones(ruta_out: str) -> Dict[str, str]:
        """
        Lee el archivo .out y separa secciones por título.

        Args:
            ruta_out: Ruta del archivo .out

        Returns:
            Diccionario con secciones {titulo: contenido}
        """
        secciones = {}
        seccion_actual = None
        contenido = []

        patron = re.compile(r'^\s*\*\*(.*?)\*\*\s*$')

        with open(ruta_out, "r", encoding="utf-8") as f:
            for linea in f:
                l = linea.rstrip()
                match = patron.match(l)

                if match:
                    if seccion_actual:
                        secciones[seccion_actual] = "\n".join(contenido)
                    seccion_actual = match.group(1).strip()
                    contenido = []
                else:
                    contenido.append(l)

        if seccion_actual:
            secciones[seccion_actual] = "\n".join(contenido)

        return secciones

    @staticmethod
    def clean_text(txt: str) -> str:
        """Limpia texto del archivo .out"""
        txt = re.sub(r'\n-+\n', '\n', txt)
        txt = re.sub(r'0(?=[A-Za-z_])', '0  ', txt)
        return txt

    @staticmethod
    def is_numeric_block(cel: str) -> bool:
        """Verifica si la celda contiene varios números"""
        patron = r'(?:[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)(?:\s+[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)+'
        return re.fullmatch(patron, cel.strip()) is not None

    def parse_section(self, secciones: Dict, name: str) -> pd.DataFrame:
        """
        Parsea una sección específica.

        Args:
            secciones: Diccionario de secciones
            name: Nombre de la sección

        Returns:
            DataFrame con datos parseados
        """
        txt = self.clean_text(secciones[name])
        filas = []

        for l in txt.split("\n"):
            l = l.strip()
            if not l:
                continue

            parts = re.split(r"\s{2,}", l)

            row = []
            for c in parts:
                c = c.strip()
                if not c:
                    continue

                if self.is_numeric_block(c):
                    row.extend(c.split())
                else:
                    row.append(c)

            filas.append(row)

        columnas = filas[0]
        datos = filas[2:]

        df = pd.DataFrame(datos, columns=columnas)
        df = df.apply(pd.to_numeric, errors="ignore").reset_index(drop=True)
        return df

    def procesar_out_file(self, ruta_out: str) -> pd.DataFrame:
        """
        Procesa un archivo .out completo de QUAL2K.

        Args:
            ruta_out: Ruta del archivo .out

        Returns:
            DataFrame consolidado con resultados
        """
        secciones = self.leer_secciones(ruta_out)

        # Mapeos de columnas
        hyd_map = {
            'Trib': 'tributary',
            'Reach': 'river_reach',
            'Downstream': 'Distancia Longitudinal (km)',
            'Hydraulics': 'flow',
            "E'": 'energy_loss',
            'H': 'hydraulic_head',
            'Btop': 'channel_top_width',
            'Ac': 'cross_section_area',
            'U': 'flow_velocity',
            'trav time': 'travel_time',
            'slope': 'channel_slope',
            'Reaeration': 'reaeration_rate',
            'Reaeration formulas': 'reaeration_method',
            'drop (m)': 'elevation_drop_m'
        }

        temps_map = {
            'Reach': 'river_reach',
            'Distance': 'Distancia Longitudinal (km)',
            'Temp(C)': 'water_temp_c'
        }

        wq_map = {
            'Trib': 'tributary',
            'Reach': 'river_reach',
            'x': 'Distancia Longitudinal (km)',
            'cond': 'conductivity',
            'ISS': 'inorganic_suspended_solids',
            'DO': 'dissolved_oxygen',
            'CBODs': 'carbonaceous_bod_slow',
            'CBODf': 'carbonaceous_bod_fast',
            'No': 'nitrite',
            'NH4': 'ammonium',
            'NO3': 'nitrate',
            'PO': 'organic_phosphorus',
            'InorgP': 'inorganic_phosphorus',
            'Phyto': 'phytoplankton',
            'INp': 'inorganic_particulate_p',
            'IPp': 'organic_particulate_p',
            'Detritus': 'detritus',
            'Pathogen': 'pathogen',
            'Alk': 'alkalinity',
            'Const i': 'const_i',
            'Const ii': 'const_ii',
            'Const iii': 'const_iii',
            'pH': 'pH',
            'Bot Alg': 'benthic_algae',
            'QNb': 'nitrogen_flow_rate',
            'QPb': 'phosphorus_flow_rate',
            'TOC': 'total_organic_carbon',
            'TN': 'total_nitrogen',
            'TP': 'total_phosphorus',
            'TKN': 'total_kjeldahl_nitrogen',
            'TSS': 'total_suspended_solids',
            'CBODu': 'ultimate_cbod',
            'NH3': 'ammonia',
            'DO sat': 'do_saturation',
            'pH sat': 'ph_saturation'
        }

        # Procesar hidráulica
        hyd = self.parse_section(secciones, 'Hydraulics Summary')
        hyd = hyd.rename(columns=hyd_map)
        hyd = hyd[['Distancia Longitudinal (km)', 'flow', 'hydraulic_head',
                   'channel_top_width', 'cross_section_area',
                   'flow_velocity', 'travel_time']]
        hyd = hyd.sort_values('Distancia Longitudinal (km)')

        # Procesar temperatura
        temps = self.parse_section(secciones, 'Temperature Summary')
        temps = temps.rename(columns=temps_map)
        temps = temps[['Distancia Longitudinal (km)', 'water_temp_c']]
        temps = temps.sort_values('Distancia Longitudinal (km)')
        temps = temps.iloc[:, 0:2]

        # Procesar calidad de agua
        wq = self.parse_section(secciones, 'Water Quality Summary')
        wq = wq.rename(columns=wq_map)
        wq = wq[['Distancia Longitudinal (km)', 'conductivity',
                 'inorganic_suspended_solids', 'dissolved_oxygen',
                 'carbonaceous_bod_slow', 'carbonaceous_bod_fast', 'nitrite',
                 'ammonium', 'nitrate', 'organic_phosphorus',
                 'inorganic_phosphorus', 'detritus', 'pathogen', 'alkalinity',
                 'const_i', 'const_ii', 'const_iii', 'pH', 'total_nitrogen',
                 'total_phosphorus', 'total_kjeldahl_nitrogen',
                 'total_suspended_solids', 'ultimate_cbod', 'ammonia']]
        wq = wq.sort_values('Distancia Longitudinal (km)')

        # Merge final
        merged = pd.merge_asof(wq, temps, on='Distancia Longitudinal (km)', direction='nearest')
        merged = pd.merge_asof(merged, hyd, on='Distancia Longitudinal (km)', direction='nearest')

        return merged.sort_values('Distancia Longitudinal (km)', ascending=False).reset_index(drop=True)

    @staticmethod
    def preparar_datos_observados(dataWQ: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara los datos observados desde el DataFrame de calidad de agua.

        Args:
            dataWQ: DataFrame con datos de calidad de agua observados

        Returns:
            DataFrame con datos observados formateados
        """
        mapeoObservados = {
            'X_QUAL2K': 'Distancia Longitudinal (km)',
            'TEMPERATURA': 'water_temp_c',
            'SST': 'total_suspended_solids',
            'OXIGENO_DISUELTO': 'dissolved_oxygen',
            'DBO5': 'carbonaceous_bod_fast',
            'NTK': 'total_kjeldahl_nitrogen',
            'NITROGENO_AMONIACAL': 'ammonium',
            'FOSFORO_TOTAL': 'total_phosphorus',
        }

        dataWQ = dataWQ.rename(columns=mapeoObservados)
        dataWQ = dataWQ[[
            'Distancia Longitudinal (km)',
            'water_temp_c',
            'total_suspended_solids',
            'dissolved_oxygen',
            'carbonaceous_bod_fast',
            'total_kjeldahl_nitrogen',
            'ammonium',
            'total_phosphorus'
        ]]

        dataWQ.columns = [f'{dataWQ.columns[i]}_obs' for i in range(dataWQ.shape[1])]
        dataWQ = dataWQ.rename(columns={'Distancia Longitudinal (km)_obs': 'Distancia Longitudinal (km)'})
        dataWQ = dataWQ.sort_values(by=['Distancia Longitudinal (km)'])

        return dataWQ

    @staticmethod
    def combinar_modelados_observados(wq_model: pd.DataFrame,
                                      data_obs: pd.DataFrame) -> pd.DataFrame:
        """
        Combina datos modelados y observados.

        Args:
            wq_model: DataFrame con datos modelados
            data_obs: DataFrame con datos observados

        Returns:
            DataFrame combinado
        """
        wq_model = wq_model.sort_values('Distancia Longitudinal (km)')
        data_obs = data_obs.sort_values('Distancia Longitudinal (km)')
        return pd.merge_asof(wq_model, data_obs,
                             on='Distancia Longitudinal (km)',
                             direction='nearest')

    @staticmethod
    def calcular_kge_global(dataExp: pd.DataFrame,
                            pares: List[Tuple[str, str]],
                            pesos: Dict[str, float]) -> Tuple[Dict[str, float], float]:
        """
        Calcula KGE por variable y KGE global ponderado.

        Args:
            dataExp: DataFrame con datos experimentales
            pares: Lista de tuplas (columna_sim, columna_obs)
            pesos: Diccionario con pesos por variable

        Returns:
            Tuple con (resultados_por_variable, kge_global)
        """
        resultados = {}
        for sim_col, obs_col in pares:
            kge_val = metricas.kge(dataExp[obs_col], dataExp[sim_col])
            resultados[sim_col] = kge_val

        global_kge = sum(resultados[var] * pesos[var] for var in resultados)

        return resultados, global_kge