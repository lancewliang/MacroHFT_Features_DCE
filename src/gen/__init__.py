"""
高频交易因子生成系统（DCE期货数据）

该包提供了从 DCE 期货数据生成高频交易因子的完整工具链。
"""

__version__ = "1.0.0"
__author__ = "MacroHFT Features Team"

from .config import (
    START_DATE,
    END_DATE,
    SYMBOL,
    COMMODITY,
    USE_MAIN_CONTRACT,
    get_dce_filepath,
    get_available_contracts,
    get_main_contract,
    get_output_filepath
)

from .data_loader import (
    load_daily_dce_data,
    load_date_range_data,
    preprocess_dce_data,
    process_dce_data,
    validate_data
)

__all__ = [
    # 配置
    "START_DATE",
    "END_DATE",
    "SYMBOL",
    "COMMODITY",
    "USE_MAIN_CONTRACT",
    "get_dce_filepath",
    "get_available_contracts",
    "get_main_contract",
    "get_output_filepath",

    # 数据加载
    "load_daily_dce_data",
    "load_date_range_data",
    "preprocess_dce_data",
    "process_dce_data",
    "validate_data",
]
