from typing import Dict, Any, List


class Q2KConfig:
    """
    Maneja todas las configuraciones del modelo QUAL2K.
    Permite modificar fácilmente parámetros del header, rates, etc.
    """

    def __init__(self, header_dict: Dict[str, Any]):
        """
        Inicializa la configuración con el diccionario de header.

        Args:
            header_dict: Diccionario con configuración del header
        """
        self.header_dict = header_dict
        self._inicializar_configuraciones_default()

    def _inicializar_configuraciones_default(self):
        """Inicializa todas las configuraciones con valores por defecto"""

        # Light data
        self.light_dict = {
            "PAR": 0.47, "kep": 0.2, "kela": 0.0088, "kenla": 0.054,
            "kess": 0.052, "kepom": 0.174,
            "solarMethod": "Bras", "nfacBras": 2, "atcRyanStolz": 0.8,
            "longatMethod": "Brunt", "fUwMethod": "Brady-Graves-Geyer",
            "Hsed": 15, "alphas": 0.0064, "rhos": 1.6, "rhow": 1,
            "Cps": 0.4, "Cpw": 1, "SedComp": "Yes"
        }

        # Diffuse sources
        self.diffuse_sources_dict = {"ndiff": 0, "sources": []}

        # Rates generales
        self.rates_dict = {
            "vss": .1, "mgC": 40, "mgN": 7.2, "mgP": 1, "mgD": 100, "mgA": 1,
            "tka": 1.024, "roc": 2.69, "ron": 4.57,
            "Ksocf": .6, "Ksona": .6, "Ksodn": .6, "Ksop": .6, "Ksob": .6,
            "khc": 0, "tkhc": 1.07, "kdcs": 0, "tkdcs": 1.047, "kdc": .09,
            "tkdc": 1.047, "khn": .015, "tkhn": 1.07, "von": .0005,
            "kn": .08, "tkn": 1.07, "ki": .1, "tki": 1.07, "vdi": .8, "tvdi": 1.07,
            "khp": .03, "tkhp": 1.07, "vop": .001, "vip": .8, "kspi": 1, "Kdpi": 1000,
            "kga": 3.8, "tkga": 1.07, "krea": .15, "tkrea": 1.07,
            "kexa": .3, "tkexa": 1.07, "kdea": .1, "tkdea": 1.07,
            "ksn": 100, "ksp": 10, "ksc": .000013, "Isat": 250,
            "khnx": 25, "va": 0, "typeF": "Zero-order",
            "kgaF": 200, "tkgaF": 1.07, "kreaF": .2, "tkreaF": 1.07,
            "kexaF": .12, "tkexaF": 1.07, "kdeaF": .1, "abmax": 1000,
            "tkdeaF": 1.07, "ksnF": 300, "kspF": 100, "kscF": .000013,
            "Isatf": 100, "khnxF": 25, "kdt": .23, "tkdt": 1.07, "ffast": 1, "vdt": .008,
            "xdum": [0, 0, 0, 0, 0, 0],
            "kai": .72, "kawindmethod": .1, "rea_extras": [72, 5, .9, .13],
            "NINpmin": .8, "NIPpmin": 1.07, "NINpupmax": 1, "NIPpupmax": 1,
            "consts": [
                {"kconst": 0, "tkconst": 1, "vconst": 0},
                {"kconst": 0, "tkconst": 1, "vconst": 0},
                {"kconst": 0, "tkconst": 1, "vconst": 0},
            ],
            "saturation_types": [
                "Exponential", "Exponential", "Exponential", "Exponential",
                "Exponential", "Half saturation", "Half saturation"
            ],
            "reaeration_methods": ["O'Connor-Dobbins", "None"],
            "reaa": 3.93, "reab": .5, "reac": 1.5
        }

        # Boundary data
        self.boundary_dict = {
            "dlstime": 0,
            "DownstreamBoundary": False,
            "nHw": 0,
            "headwaters": []
        }

        # Hydraulics data
        self.hydraulics_data_dict = {
            "nhydda": 0,
            "data": []
        }

        # Diel data
        self.diel_dict = {"ndiel": 5, "idiel": 1, "ndielstat": 0, "stations": [0]}

    def generar_reach_rates_default(self, n: int) -> Dict[str, Any]:
        """
        Genera un diccionario de reach_rates con valores por defecto.

        Args:
            n: Número de tramos

        Returns:
            Diccionario de reach_rates
        """
        return {
            "nr": n,
            "reaches": [
                {
                    "kaaa": None, "vss_rch": None, "khc_rch": None,
                    "kdcs_rch": None, "kdc_rch": None, "khn_rch": None,
                    "von_rch": None, "kn_rch": 0.001, "ki_rch": None,
                    "vdi_rch": None, "khp_rch": None, "vop_rch": None,
                    "vip_rch": None, "kga_rch": None, "krea_rch": None,
                    "kexa_rch": None, "kdea_rch": None, "va_rch": None,
                    "kgaF_rch": None, "kreaF_rch": None, "kexaF_rch": None,
                    "kdeaF_rch": None, "kdt_rch": None, "vdt_rch": None,
                    "ffast_rch": None
                }
                for _ in range(n)
            ]
        }

    def generar_reach_rates_custom(self, n: int,
                                   kaaa_list: List = None,
                                   khc_list: List = None,
                                   kdcs_list: List = None,
                                   kdc_list: List = None,
                                   khn_list: List = None,
                                   kn_list: List = None,
                                   ki_list: List = None,
                                   khp_list: List = None,
                                   kdt_list: List = None) -> Dict[str, Any]:
        """
        Genera un diccionario de reach_rates personalizado.

        Args:
            n: Número de tramos
            kaaa_list: Lista de métodos de reaireación
            khc_list: Lista de tasas de hidrólisis de C
            kdcs_list: Lista de tasas de descomposición particulada
            kdc_list: Lista de tasas de oxidación disuelta
            khn_list: Lista de tasas de hidrólisis de Norg
            kn_list: Lista de tasas de nitrificación
            ki_list: Lista de tasas de inhibición por OD
            khp_list: Lista de tasas de hidrólisis de Porg
            kdt_list: Lista de tasas de descomposición de detrito

        Returns:
            Diccionario de reach_rates
        """
        # Valores por defecto si no se proporcionan
        if kaaa_list is None: kaaa_list = [None] * n
        if khc_list is None: khc_list = [None] * n
        if kdcs_list is None: kdcs_list = [None] * n
        if kdc_list is None: kdc_list = [None] * n
        if khn_list is None: khn_list = [None] * n
        if kn_list is None: kn_list = [None] * n
        if ki_list is None: ki_list = [None] * n
        if khp_list is None: khp_list = [None] * n
        if kdt_list is None: kdt_list = [None] * n

        # Validación
        listas = [kaaa_list, khc_list, kdcs_list, kdc_list, khn_list,
                  kn_list, ki_list, khp_list, kdt_list]
        if any(len(lst) != n for lst in listas):
            raise ValueError("Todas las listas deben tener longitud igual a n")

        reaches = []
        for i in range(n):
            tramo = {
                "kaaa": kaaa_list[i],
                "vss_rch": None,
                "khc_rch": khc_list[i],
                "kdcs_rch": kdcs_list[i],
                "kdc_rch": kdc_list[i],
                "khn_rch": khn_list[i],
                "von_rch": None,
                "kn_rch": kn_list[i],
                "ki_rch": ki_list[i],
                "vdi_rch": None,
                "khp_rch": khp_list[i],
                "vop_rch": None,
                "vip_rch": None,
                "kga_rch": None,
                "krea_rch": None,
                "kexa_rch": None,
                "kdea_rch": None,
                "va_rch": None,
                "kgaF_rch": None,
                "kreaF_rch": None,
                "kexaF_rch": None,
                "kdeaF_rch": None,
                "kdt_rch": kdt_list[i],
                "vdt_rch": None,
                "ffast_rch": None
            }
            reaches.append(tramo)

        return {
            "nr": n,
            "reaches": reaches
        }

    def actualizar_header(self, **kwargs):
        """
        Actualiza valores del header.

        Ejemplo:
            config.actualizar_header(rivname="Nuevo Rio", tf=10)
        """
        self.header_dict.update(kwargs)

    def actualizar_rates(self, **kwargs):
        """
        Actualiza valores de las tasas cinéticas.

        Ejemplo:
            config.actualizar_rates(kn=0.1, ki=0.2)
        """
        self.rates_dict.update(kwargs)

    def actualizar_light(self, **kwargs):
        """
        Actualiza parámetros de luz.

        Ejemplo:
            config.actualizar_light(PAR=0.5, kep=0.3)
        """
        self.light_dict.update(kwargs)