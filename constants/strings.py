"""
固定字符串常量定义
使用场景：不需要参数的固定字符串
"""

GLOBE = "? SETUP GLOBAL ? "
FLOWSHEET_GLOBAL = "? %M FLOWSHEET GLOBAL ?"
COMPONENTS_GLOBLE = "? COMPONENTS MAIN ? "
GOPSETNAME_GLOBLE = "? %M PROPERTIES MAIN ? "
DATABANKS_GLOBE = "? %M DATABANKS ? "
# 环境配置 (Setup & Units)
class Environment:
    # 正确格式的 Aspen .bkp 文件头
    ASPEN_HEADER_STANDARD = r'''ASPEN "40.0" DATETIME "01/07/2026  17:18:06:99" MACHINE "WIN-X64" SITEID "" USER "Administrator"'''
    # MET (公制)
    MET = r''' ? SETUP UNITS-SET SET1 ? \ UNITSET BASESET = SI (1 1 1 1 1 1 1 1 1 1 6 1 1 1 1 
 1 1 1 1 19 1 4 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 
 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 17 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 
 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1  
 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1) \ '''
    # 告诉软件，“我接下来输入的所有数据，都默认使用刚才定义的 SET1 单位集”。
    SET1 = r"""\ IN-UNITS INSET = SET1 \ """

    unit = f'''? SETUP GLOBAL ? \n\ IN-UNITS INSET = SI \\'''




