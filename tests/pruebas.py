
reach_rates_custom = model.config.generar_reach_rates_custom(
    n=n,
    kaaa_list=[None] * n, # Tasa de aireación
    khc_list=[None] * n, # Hidrólisis de carbono
    kdcs_list=[None] * n, # Descomposición de carbono lento
    kdc_list=[None] * n, # Descomposición de carbono rápido
    khn_list=[None] * n, # Hidrólisis de nitrógeno
    kn_list=[None] * n, # Nitrificación
    ki_list=[None] * n, # Tasa de denitricación
    khp_list=[None] * n, # Hidrólisis de fósforo
    kdt_list=[None] * n # Detritos
)
