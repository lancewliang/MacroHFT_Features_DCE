"""
铝高频交易因子生成系统
"""

__version__ = "1.0.0"

from .config import (
    START_DATE,
    END_DATE,
    SYMBOL,
    COMMODITY,
    get_output_filepath,
    ensure_directories,
)

from .feature_calculator import get_feature_columns

from .data_loader import (
    load_daily_orderbook_data,
    load_and_merge_date_range,
)

__all__ = [
    "START_DATE",
    "END_DATE",
    "SYMBOL",
    "COMMODITY",
    "get_output_filepath",
    "get_feature_columns",
    "ensure_directories",
    "load_daily_orderbook_data",
    "load_and_merge_date_range",
]
