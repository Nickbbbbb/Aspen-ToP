class ChemicalMapper:
    """化工物质映射器 (带分子量版)"""

    # 物质数据库
    # 格式: [本地名称, Aspen的label, Aspen分子式, 中文名, 分子量(g/mol), aspen的名字, cas号]
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
        ["WATER", "WATER", "H2O", "", 18.015, "WATER", "7732-18-5"],
        ["ETHANOL", "ETHAN-02", "C2H6O-2", "", 341.44, "ETHANOL", "64-17-5"]
    ]

    # 物质名称和组分id的对应 (可能会发生变化)
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
    def get_by_local_name(cls, local_name: str, case_sensitive: bool = False) -> dict:
        """根据本地名称获取物质信息"""
        search_name = local_name if case_sensitive else local_name.lower()

        for chem in cls.CHEMICAL_DB:
            db_local = chem[0] if case_sensitive else chem[0].lower()
            if db_local == search_name:
                return {
                    "local_name": chem[0],
                    "aspen_name": chem[1],
                    "aspen_formula": chem[2],
                    "chinese_name": chem[3],
                    "mw": chem[4],
                    "aspen_fullname": chem[5],
                    "cas": chem[6]
                }
        return None

    @classmethod
    def get_by_aspen_name(cls, aspen_name: str) -> dict:
        """根据Aspen名称获取物质信息 (支持模糊匹配)"""
        target = aspen_name.strip().upper()

        for chem in cls.CHEMICAL_DB:
            # 1. 匹配Aspen标签 (如 ETHAN-01)
            if chem[1].upper() == target:
                return cls._format_result(chem)

            # 2. 匹配Aspen完整名称 (如 ETHANE)
            if chem[5].upper() == target:
                return cls._format_result(chem)

            # 3. 匹配本地名称
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

    @classmethod
    def get_local_name_by_aspen(cls, aspen_name: str) -> str:
        """
        根据Aspen名称获取本地名称

        Args:
            aspen_name: Aspen中的名称，可以是标签(如ETHAN-01)或完整名(如ETHANE)

        Returns:
            本地名称字符串，如"METHANE"
        """
        info = cls.get_by_aspen_name(aspen_name)
        if info:
            return info["local_name"]

        # 如果找不到，尝试去除末尾数字再匹配
        if "-" in aspen_name:
            base_name = aspen_name.split("-")[0]
            for chem in cls.CHEMICAL_DB:
                if chem[1].startswith(base_name):
                    return chem[0]

        return None

    @classmethod
    def get_aspen_name_by_local(cls, local_name: str, use_label: bool = True, case_sensitive: bool = False) -> str:
        """
        根据本地名称获取Aspen名称

        Args:
            local_name: 本地名称，如"METHANE"
            use_label: True返回标签(如METHA-01)，False返回完整名(如METHANE)
            case_sensitive: 是否区分大小写

        Returns:
            Aspen名称字符串
        """
        info = cls.get_by_local_name(local_name, case_sensitive)
        if info:
            return info["aspen_name"] if use_label else info["aspen_fullname"]
        return None

    @classmethod
    def get_aspen_info_by_local(cls, local_name: str, case_sensitive: bool = False) -> dict:
        """
        根据本地名称获取完整的Aspen信息(包含标签和完整名)

        Args:
            local_name: 本地名称
            case_sensitive: 是否区分大小写

        Returns:
            dict: 包含aspen_label和aspen_fullname
        """
        info = cls.get_by_local_name(local_name, case_sensitive)
        if info:
            return {
                "aspen_label": info["aspen_name"],  # 标签: METHA-01
                "aspen_fullname": info["aspen_fullname"],  # 完整名: METHANE
                "local_name": info["local_name"],  # 本地名: METHANE
                "formula": info["aspen_formula"],  # 分子式: CH4
                "mw": info["mw"]  # 分子量
            }
        return None

    @classmethod
    def get_local_info_by_aspen(cls, aspen_name: str) -> dict:
        """
        根据Aspen名称获取完整的本地信息

        Args:
            aspen_name: Aspen中的名称

        Returns:
            dict: 包含所有信息
        """
        info = cls.get_by_aspen_name(aspen_name)
        if info:
            return {
                "local_name": info["local_name"],
                "aspen_label": info["aspen_name"],
                "aspen_fullname": info["aspen_fullname"],
                "formula": info["aspen_formula"],
                "chinese_name": info["chinese_name"],
                "mw": info["mw"],
                "cas": info["cas"]
            }
        return None

    @classmethod
    def get_mw_list(cls, aspen_comp_names: list) -> list:
        """
        工具方法：传入一组 Aspen 组分名，返回对应的分子量列表。
        找不到的组分默认 MW=0.0
        """
        mws = []
        for name in aspen_comp_names:
            info = cls.get_by_aspen_name(name)
            if info:
                mws.append(info["mw"])
            else:
                print(f"⚠️ 警告: 数据库中未找到组分 [{name}] 的分子量，将使用 0.0")
                mws.append(0.0)
        return mws

    @classmethod
    def get_local_names(cls, aspen_comp_names: list) -> list:
        """
        批量转换Aspen名称为本地名称
        """
        local_names = []
        for name in aspen_comp_names:
            local_name = cls.get_local_name_by_aspen(name)
            if local_name:
                local_names.append(local_name)
            else:
                print(f"⚠️ 警告: 未找到 [{name}] 对应的本地名称")
                local_names.append(name)  # 如果找不到，返回原名称
        return local_names

    @classmethod
    def get_aspen_labels(cls, local_names: list, use_label: bool = True) -> list:
        """
        批量转换本地名称为Aspen名称
        """
        aspen_names = []
        for name in local_names:
            aspen_name = cls.get_aspen_name_by_local(name, use_label)
            if aspen_name:
                aspen_names.append(aspen_name)
            else:
                print(f"⚠️ 警告: 未找到 [{name}] 对应的Aspen名称")
                aspen_names.append(name)  # 如果找不到，返回原名称
        return aspen_names

    @classmethod
    def add_chemical(cls, local_name: str, aspen_name: str, aspen_formula: str, chinese_name: str = "",
                     mw: float = 0.0, aspen_fullname: str = "", cas: str = ""):
        """添加新物质"""
        cls.CHEMICAL_DB.append([local_name, aspen_name, aspen_formula, chinese_name, mw, aspen_fullname, cas])


# =================使用示例=================
if __name__ == "__main__":
    # 1. 根据Aspen名称获取本地名称
    print("=== 根据Aspen名称获取本地名称 ===")
    test_names = ["METHA-01", "ETHAN-01", "PROPA-02", "WATER", "CARBO-02"]
    for aspen_name in test_names:
        local_name = ChemicalMapper.get_local_name_by_aspen(aspen_name)
        print(f"Aspen: {aspen_name} -> 本地: {local_name}")

    print("\n=== 根据本地名称获取Aspen名称 ===")
    # 2. 根据本地名称获取Aspen名称
    test_locals = ["METHANE", "ETHANE", "PROPANE", "WATER", "CARBON DIOXIDE"]
    for local_name in test_locals:
        aspen_label = ChemicalMapper.get_aspen_name_by_local(local_name, use_label=True)
        aspen_full = ChemicalMapper.get_aspen_name_by_local(local_name, use_label=False)
        print(f"本地: {local_name} -> Aspen标签: {aspen_label}, Aspen完整名: {aspen_full}")

    print("\n=== 批量转换示例 ===")
    # 3. 批量转换
    aspen_list = ["METHA-01", "ETHAN-01", "WATER"]
    local_list = ChemicalMapper.get_local_names(aspen_list)
    print(f"Aspen列表: {aspen_list} -> 本地列表: {local_list}")

    # 4. 获取完整信息
    print("\n=== 获取完整信息 ===")
    methane_info = ChemicalMapper.get_local_info_by_aspen("METHA-01")
    print(f"METHANE信息: {methane_info}")

    # 5. 分子量获取
    mw_list = ChemicalMapper.get_mw_list(["METHA-01", "ETHAN-01", "WATER"])
    print(f"\n分子量列表: {mw_list}")