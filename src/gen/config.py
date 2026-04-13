"""
配置文件
"""

from pathlib import Path
from datetime import datetime

# ==================== 项目路径配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUT_ROOT = PROJECT_ROOT / "output"

# ==================== 品种配置 ====================
COMMODITY = "铝"
SYMBOL = "al"
TIMEFRAME = "30s"
# ==================== 数据时间范围配置 ====================
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"
# ==================== 输出配置 ====================
FEATURES_OUTPUT_DIR = OUTPUT_ROOT / "features"
OUTPUT_FORMAT = "feather"  # "parquet", "feather", "csv"

# ==================== 处理参数 ====================
BATCH_SIZE_DAYS = 4000

# ==================== 订单簿列配置 ====================
ORDERBOOK_REQUIRED_COLUMNS = [
    "datetime", "minute", "is_consecutive_minute",
    "open_price", "high_price", "low_price", "close_price",
    "total_trade_volume", "turnover", "open_interest",
    *[f"bid{i}_price" for i in range(1, 6)],
    *[f"bid{i}_size" for i in range(1, 6)],
    *[f"ask{i}_price" for i in range(1, 6)],
    *[f"ask{i}_size" for i in range(1, 6)],
]

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / f"feature_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# ==================== 性能配置 ====================
SHOW_PROGRESS = True

def get_output_filepath(date_str: str = None, month_str: str = None,
                        start_date: str = None,
                        end_date: str = None,
                        timeframe: str = None,
                        ) -> Path:
    """
    获取输出文件路径

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD' (用于单文件输出)
        month_str: 月份字符串，格式 'YYYYMM' (用于按月输出)
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        timeframe: 时间粒度 (例: '30s' 或 '1m')，如果提供则包含在文件名中

    Returns:
        Path: 输出文件路径
    """
    FEATURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tf_suffix = f"_{timeframe}" if timeframe else ""

    if month_str:
        filename = f"features_{month_str}{tf_suffix}.{OUTPUT_FORMAT}"
    elif date_str:
        filename = f"features_{date_str.replace('-', '')}{tf_suffix}.{OUTPUT_FORMAT}"
    elif start_date and end_date:
        filename = f"features_{start_date.replace('-', '')}_{end_date.replace('-', '')}{tf_suffix}.{OUTPUT_FORMAT}"
    else:
        filename = f"features{tf_suffix}.{OUTPUT_FORMAT}"

    return FEATURES_OUTPUT_DIR / filename


def ensure_directories():
    """确保所有必要的目录存在"""
    FEATURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

