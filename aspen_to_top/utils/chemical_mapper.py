class ChemicalMapper:
    """化工物质映射器"""

    CHEMICAL_DB = [
        ["HYDROGEN", "HYDROGEN", "H2", "", 2.016, "HYDROGEN", "1333-74-0"],
        ["CARBON MONOXIDE", "CARBO-01", "CO", "", 28.010, "CARBON-MONOXIDE", "630-08-0"],
        ["CARBON DIOXIDE", "CARBO-02", "CO2", "", 44.010, "CARBON-DIOXIDE", "124-38-9"],
        ["HYDROGEN SULFIDE", "HYDRO-02", "H2S", "", 34.082, "HYDROGEN-SULFIDE", "7783-06-4"],
        ["METHANE", "METHA-01", "CH4", "", 16.043, "METHANE", "74-82-8"],
        ["ACETYLENE", "ACETY-01", "C2H2", "", 26.038, "ACETYLENE", "74-86-2"],
        ["ETHYLENE", "ETHYL-01", "C2H4", "", 28.054, "ETHYLENE", "74-85-1"],
        ["ETHANE", "ETHAN-01", "C2H6", "", 30.070, "ETHANE", "74-84-0"],
        ["METHYLACETYLENE", "METHY-01", "C3H4-2", "", 40.065, "METHYL-ACETYLENE", "74-99-7"],
        ["PROPADIENE", "PROPA-01", "C3H4-1", "", 40.065, "PROPADIENE", "463-49-0"],
        ["PROPYLENE", "PROPY-01", "C3H6-2", "", 42.081, "PROPYLENE", "115-07-1"],
        ["PROPANE", "PROPA-02", "C3H8", "", 44.096, "PROPANE", "74-98-6"],
        ["1,3-BUTADIENE", "1:3-B-01", "C4H6-4", "", 54.092, "1,3-BUTADIENE", "106-99-0"],
        ["ETHYLACETYLENE", "1-BUT-01", "C4H6-1", "", 54.092, "1-BUTYNE", "107-00-6"],
        ["1-BUTENE", "1-BUT-02", "C4H8-1", "", 56.108, "1-BUTENE", "106-98-9"],
        ["n-BUTANE", "N-BUT-01", "C4H10-1", "", 58.124, "N-BUTANE", "106-97-8"],
        ["n-PENTANE", "N-PEN-01", "C5H12-1", "", 72.151, "N-PENTANE", "109-66-0"],
        ["ISOPENTANE", "2-MET-01", "C5H12-2", "", 72.151, "2-METHYL-BUTANE", "78-78-4"],
        ["BENZENE", "BENZE-01", "C6H6", "", 78.114, "BENZENE", "71-43-2"],
        ["n-HEXANE", "N-HEX-01", "C6H14-1", "", 86.178, "N-HEXANE", "110-54-3"],
        ["CYCLOHEXANE", "CYCLO-01", "C6H12-1", "", 84.161, "CYCLOHEXANE", "110-82-7"],
        ["TOLUENE", "TOLUE-01", "C7H8", "", 92.141, "TOLUENE", "108-88-3"],
        ["n-HEPTANE", "N-HEP-01", "C7H16-1", "", 100.205, "N-HEPTANE", "142-82-5"],
        ["METHYLCYCLOHEXANE", "METHY-02", "C7H14-6", "", 98.188, "METHYLCYCLOHEXANE", "108-87-2"],
        ["STYRENE", "STYRE-01", "C8H8", "", 104.152, "STYRENE", "100-42-5"],
        ["m-XYLENE", "M-XYL-01", "C8H10-2", "", 106.168, "M-XYLENE", "108-38-3"],
        ["ETHYLBENZENE", "ETHYL-02", "C8H10-4", "", 106.168, "ETHYLBENZENE", "100-41-4"],
        ["n-OCTANE", "N-OCT-01", "C8H18-1", "", 114.232, "N-OCTANE", "111-65-9"],
        ["2,2,4-TRIMETHYLPENTANE", "2:2:4-01", "C8H18-13", "", 114.232, "2,2,4-TRIMETHYLPENTANE", "540-84-1"],
        ["1,2,3-TRIMETHYLBENZENE", "1:2:3-01", "C9H12-6", "", 120.195, "1,2,3-TRIMETHYLBENZENE", "526-73-8"],
        ["n-NONANE", "N-NON-01", "C9H20-1", "", 128.259, "N-NONANE", "111-84-2"],
        ["NITROGEN", "NITROGEN", "N2", "", 28.013, "NITROGEN", "7727-37-9"],
        ["WATER", "WATER", "H2O", "", 18.015, "WATER", "7732-18-5"],
        ["ETHANOL", "ETHAN-02", "C2H6O-2", "", 341.44, "ETHANOL", "64-17-5"]
    ]

    CHEMICAL_MAP = {
        "1333-74-0": "2020063412281794561",
        "630-08-0": "2020063412290183170",
        "124-38-9": "2020063412294377473",
        "7783-06-4": "2020063412298571777",
        "74-86-2": "2020063412302766082",
        "74-84-0": "2020063412311154689",
        "74-99-7": "2020063412315348994",
        "463-49-0": "2020063412319543297",
        "115-07-1": "2020063412319543298",
        "74-98-6": "2020063412323737601",
        "106-99-0": "2020063412327931906",
        "107-00-6": "2020063412332126209",
        "106-98-9": "2020063412336320513",
        "106-97-8": "2020063412336320514",
        "109-66-0": "2020063412340514818",
        "78-78-4": "2020063412344709121",
        "74-82-8": "2020041490760327170",
        "74-85-1": "2020041490768715778",
        "71-43-2": "2020063412348903426",
        "110-54-3": "2020063412353097730",
        "110-82-7": "2020063412353097731",
        "108-88-3": "2020063412357292034",
        "142-82-5": "2020063412361486337",
        "108-87-2": "2020063412365680642",
        "100-42-5": "2020063412369874945",
        "108-38-3": "2020063412369874946",
        "100-41-4": "2020063412374069249",
        "111-65-9": "2020063412378263554",
        "540-84-1": "2020063412382457857",
        "526-73-8": "2020063412382457858",
        "111-84-2": "2020063412386652161",
        "7732-18-5": "2020063412390846465",
        "64-17-5": "2020701588289609730",
        "75-28-5": "2037096433409187841",
        "92-52-4": "2037104457288900610"
    }

    @classmethod
    def get_local_name_by_aspen(cls, aspen_name: str) -> str:
        info = cls.get_by_aspen_name(aspen_name)
        if info:
            return info["local_name"]
        if "-" in aspen_name:
            base_name = aspen_name.split("-")[0]
            for chem in cls.CHEMICAL_DB:
                if chem[1].startswith(base_name):
                    return chem[0]
        return None

    @classmethod
    def get_by_aspen_name(cls, aspen_name: str) -> dict:
        target = aspen_name.strip().upper()
        for chem in cls.CHEMICAL_DB:
            if chem[1].upper() == target:
                return cls._format_result(chem)
            if chem[5].upper() == target:
                return cls._format_result(chem)
            if chem[0].upper() == target:
                return cls._format_result(chem)
        return None

    @classmethod
    def _format_result(cls, chem_row):
        return {
            "local_name": chem_row[0],
            "aspen_name": chem_row[1],
            "aspen_formula": chem_row[2],
            "chinese_name": chem_row[3],
            "mw": chem_row[4],
            "aspen_fullname": chem_row[5],
            "cas": chem_row[6]
        }
