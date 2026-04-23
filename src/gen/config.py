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

def normalize_symbol(symbol: str) -> str:
    """
    规范化品种缩写，统一输出目录命名。
    """
    symbol_value = (symbol or SYMBOL).strip().lower()
    if not symbol_value:
        raise ValueError("symbol 不能为空")
    return symbol_value


def get_symbol_output_root(symbol: str = SYMBOL) -> Path:
    """
    获取品种专属输出根目录：output/<symbol>
    """
    return OUTPUT_ROOT / normalize_symbol(symbol)


def get_features_output_dir(symbol: str = SYMBOL) -> Path:
    """
    获取特征输出目录：output/<symbol>/features
    """
    return get_symbol_output_root(symbol) / "features"


def get_factor_validation_dir(symbol: str = SYMBOL) -> Path:
    """
    获取因子验证输出目录：output/<symbol>/factor_validation
    """
    return get_symbol_output_root(symbol) / "factor_validation"


# 兼容旧逻辑：默认 symbol 的输出目录常量
FEATURES_OUTPUT_DIR = get_features_output_dir()
FACTOR_VALIDATION_DIR = get_factor_validation_dir()


def get_output_filepath(date_str: str = None, month_str: str = None,
                        start_date: str = None,
                        end_date: str = None,
                        timeframe: str = None,
                        symbol: str = SYMBOL,
                        ) -> Path:
    """
    获取输出文件路径

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD' (用于单文件输出)
        month_str: 月份字符串，格式 'YYYYMM' (用于按月输出)
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        timeframe: 时间粒度 (例: '30s' 或 '1m')，如果提供则包含在文件名中
        symbol: 品种缩写 (例: 'al'、'fu')

    Returns:
        Path: 输出文件路径
    """
    features_output_dir = get_features_output_dir(symbol)
    features_output_dir.mkdir(parents=True, exist_ok=True)

    tf_suffix = f"_{timeframe}" if timeframe else ""

    if month_str:
        filename = f"features_{month_str}{tf_suffix}.{OUTPUT_FORMAT}"
    elif date_str:
        filename = f"features_{date_str.replace('-', '')}{tf_suffix}.{OUTPUT_FORMAT}"
    elif start_date and end_date:
        filename = f"features_{start_date.replace('-', '')}_{end_date.replace('-', '')}{tf_suffix}.{OUTPUT_FORMAT}"
    else:
        filename = f"features{tf_suffix}.{OUTPUT_FORMAT}"

    return features_output_dir / filename


def ensure_directories(symbol: str = SYMBOL):
    """确保所有必要的目录存在"""
    get_features_output_dir(symbol).mkdir(parents=True, exist_ok=True)
    get_factor_validation_dir(symbol).mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
