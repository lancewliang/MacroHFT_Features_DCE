"""
高频交易因子生成系统

该包提供了从 Binance 期货数据生成高频交易因子的完整工具链。
"""

__version__ = "1.0.0"
__author__ = "MacroHFT Features Team"

from .config import (
    START_DATE,
    END_DATE,
    SYMBOL,
    get_bookdepth_filepath,
    get_kline_filepath,
    get_output_filepath
)

from .data_loader import (
    load_daily_bookdepth,
    load_daily_kline,
    load_date_range_data,
    pivot_bookdepth,
    preprocess_kline,
    merge_data,
    validate_data
)

from .feature_calculator import (
    calculate_kline_features,
    calculate_volume_and_normalized_size,
    calculate_wap_features,
    calculate_spread_features,
    calculate_volume_features,
    calculate_vwap_features,
    calculate_log_return_features,
    calculate_all_features,
    get_feature_columns
)

__all__ = [
    # 配置
    "START_DATE",
    "END_DATE",
    "SYMBOL",
    "get_bookdepth_filepath",
    "get_kline_filepath",
    "get_output_filepath",

    # 数据加载
    "load_daily_bookdepth",
    "load_daily_kline",
    "load_date_range_data",
    "pivot_bookdepth",
    "preprocess_kline",
    "merge_data",
    "validate_data",

    # 因子计算
    "calculate_kline_features",
    "calculate_volume_and_normalized_size",
    "calculate_wap_features",
    "calculate_spread_features",
    "calculate_volume_features",
    "calculate_vwap_features",
    "calculate_log_return_features",
    "calculate_all_features",
    "get_feature_columns",
]
