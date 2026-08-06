"""
Índice de Calidad del Agua (ICA) en corrientes superficiales.

Implementación de la metodología oficial del IDEAM (Hoja metodológica
GCI-OE-F002, versión 1.4, 2025), variante de 6 variables: oxígeno disuelto
(% saturación), sólidos suspendidos totales, demanda química de oxígeno,
conductividad eléctrica, pH y relación nitrógeno total/fósforo total.
"""

import numpy as np
import pandas as pd

PESOS_ICA_6 = {
    'od': 0.17,
    'sst': 0.17,
    'dqo': 0.17,
    'ce': 0.17,
    'nt_pt': 0.17,
    'ph': 0.15,
}


def subindice_od(ps_od: pd.Series) -> pd.Series:
    """Subíndice de oxígeno disuelto a partir del % de saturación."""
    i = np.where(ps_od <= 100, 0.01 * ps_od, 2 - 0.01 * ps_od)
    return pd.Series(np.clip(i, 0, 1), index=ps_od.index)


def subindice_sst(sst: pd.Series) -> pd.Series:
    """Subíndice de sólidos suspendidos totales (mg/L)."""
    i = 1.02 - 0.003 * sst
    i = np.where(sst <= 4.5, 1.0, i)
    i = np.where(sst >= 320, 0.0, i)
    return pd.Series(np.clip(i, 0, 1), index=sst.index)


def subindice_dqo(dqo: pd.Series) -> pd.Series:
    """Subíndice de demanda química de oxígeno (mg/L)."""
    condiciones = [dqo <= 20, dqo <= 25, dqo <= 40, dqo <= 80]
    valores = [0.91, 0.71, 0.51, 0.26]
    return pd.Series(np.select(condiciones, valores, default=0.125), index=dqo.index)


def subindice_ce(ce: pd.Series) -> pd.Series:
    """Subíndice de conductividad eléctrica (uS/cm)."""
    i = 1 - 10 ** (-3.26 + 1.34 * np.log10(ce))
    return pd.Series(np.clip(i, 0, 1), index=ce.index)


def subindice_ph(ph: pd.Series) -> pd.Series:
    """Subíndice de pH."""
    condiciones = [ph < 4, ph <= 7, ph <= 8, ph <= 11]
    valores = [
        0.1,
        0.02628419 * np.exp(ph * 0.520025),
        1.0,
        np.exp((ph - 8) * -0.5187742),
    ]
    return pd.Series(np.select(condiciones, valores, default=0.1), index=ph.index)


def subindice_nt_pt(nt_pt: pd.Series) -> pd.Series:
    """Subíndice de la relación nitrógeno total/fósforo total (adimensional)."""
    condiciones = [nt_pt.between(15, 20), (nt_pt > 10) & (nt_pt < 15), (nt_pt > 5) & (nt_pt <= 10)]
    valores = [0.8, 0.6, 0.35]
    return pd.Series(np.select(condiciones, valores, default=0.15), index=nt_pt.index)


def categorizar(ica: pd.Series) -> pd.Series:
    """Descriptor de calidad (Bueno/Aceptable/Regular/Malo/Muy malo) según el valor de ICA."""
    condiciones = [ica >= 0.91, ica >= 0.71, ica >= 0.51, ica >= 0.26]
    valores = ['Bueno', 'Aceptable', 'Regular', 'Malo']
    return pd.Series(np.select(condiciones, valores, default='Muy malo'), index=ica.index)


def calcular_ica(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega al DataFrame los subíndices, el ICA (6 variables) y su categoría.

    Espera las columnas producidas por Q2KResultsAnalyzer.procesar_out_file():
    do_saturation_pct, total_suspended_solids, dqo_calculada, conductivity,
    pH, total_nitrogen, total_phosphorus.
    """
    df = df.copy()
    nt_pt = df['total_nitrogen'] / df['total_phosphorus']

    df['subindice_od'] = subindice_od(df['do_saturation_pct'])
    df['subindice_sst'] = subindice_sst(df['total_suspended_solids'])
    df['subindice_dqo'] = subindice_dqo(df['dqo_calculada'])
    df['subindice_ce'] = subindice_ce(df['conductivity'])
    df['subindice_ph'] = subindice_ph(df['pH'])
    df['subindice_nt_pt'] = subindice_nt_pt(nt_pt)

    df['ica'] = (
        df['subindice_od'] * PESOS_ICA_6['od']
        + df['subindice_sst'] * PESOS_ICA_6['sst']
        + df['subindice_dqo'] * PESOS_ICA_6['dqo']
        + df['subindice_ce'] * PESOS_ICA_6['ce']
        + df['subindice_nt_pt'] * PESOS_ICA_6['nt_pt']
        + df['subindice_ph'] * PESOS_ICA_6['ph']
    )
    df['categoria_ica'] = categorizar(df['ica'])
    return df
