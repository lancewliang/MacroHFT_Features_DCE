"""
配置文件
包含所有数据路径、参数和常量配置
"""

from pathlib import Path
from datetime import datetime

# ==================== 项目路径配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUT_ROOT = PROJECT_ROOT / "output"

# ==================== 数据源配置 ====================
# 订单簿数据路径
BOOKDEPTH_BASE_PATH = DATA_ROOT / "futures" / "um" / "daily" / "bookDepth" / "ETHUSDT"

# K线数据路径
KLINE_BASE_PATH = DATA_ROOT / "futures" / "um" / "daily" / "klines" / "ETHUSDT" / "1m"

# 示例数据路径（用于测试）
EXAMPLE_DATA_PATH = PROJECT_ROOT / "biance_example"

# ==================== 交易对配置 ====================
SYMBOL = "ETHUSDT"
TIMEFRAME = "1m"

# ==================== 数据时间范围配置 ====================
START_DATE = "2023-01-01"
END_DATE = "2026-01-01"

# ==================== 文件命名模板 ====================
# 订单簿文件名模板：ETHUSDT-bookDepth-2023-06-30.zip
BOOKDEPTH_FILENAME_TEMPLATE = "{symbol}-bookDepth-{date}.zip"

# K线文件名模板：ETHUSDT-1m-2023-06-30.zip
KLINE_FILENAME_TEMPLATE = "{symbol}-{timeframe}-{date}.zip"

# ==================== 输出配置 ====================
# 输出目录
FEATURES_OUTPUT_DIR = OUTPUT_ROOT / "features"

# 输出文件格式
OUTPUT_FORMAT = "feather"  # 可选: "parquet", "feather" 或 "csv"

# 输出文件命名策略
OUTPUT_STRATEGY = "single"  # 可选: "single" (单文件) 或 "monthly" (按月分割)

# ==================== 处理参数配置 ====================
# 批处理大小（天数）
BATCH_SIZE_DAYS = 2000

# 是否使用懒加载
USE_LAZY_LOADING = True

# 并行处理线程数（0 表示自动）
N_THREADS = 0

# ==================== 订单簿配置 ====================
# 订单簿档位映射
BID_LEVELS = [-1, -2, -3, -4, -5]  # 买方五档
ASK_LEVELS = [1, 2, 3, 4, 5]       # 卖方五档
ALL_LEVELS = BID_LEVELS + ASK_LEVELS

# 档位名称映射
LEVEL_NAMES = {
    -1: "bid1", -2: "bid2", -3: "bid3", -4: "bid4", -5: "bid5",
    1: "ask1", 2: "ask2", 3: "ask3", 4: "ask4", 5: "ask5"
}

# ==================== K线数据列配置 ====================
KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "count",
    "taker_buy_volume", "taker_buy_quote_volume", "ignore"
]

# 重命名映射
KLINE_RENAME_MAP = {
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "close": "close_price",
    "volume": "traded_volume"
}

# ==================== 因子配置 ====================
# K线特征因子列表
KLINE_FEATURES = [
    "kmid", "kmid2", "klen",
    "kup", "kup2",
    "klow", "klow2",
    "ksft", "ksft2"
]

# 归一化订单量因子
SIZE_N_FEATURES = [
    "bid1_size_n", "bid2_size_n", "bid3_size_n", "bid4_size_n", "bid5_size_n",
    "ask1_size_n", "ask2_size_n", "ask3_size_n", "ask4_size_n", "ask5_size_n"
]

# WAP 因子
WAP_FEATURES = ["wap_1", "wap_2", "wap_balance"]

# 价差因子
SPREAD_FEATURES = ["buy_spread", "sell_spread", "price_spread"]

# 成交量因子
VOLUME_FEATURES = ["buy_volume", "sell_volume", "volume_imbalance"]

# VWAP 因子
VWAP_FEATURES = ["buy_vwap", "sell_vwap"]

# 对数收益率因子
LOG_RETURN_FEATURES = [
    "log_return_bid1_price", "log_return_bid2_price",
    "log_return_ask1_price", "log_return_ask2_price",
    "log_return_wap_1", "log_return_wap_2"
]

# 趋势因子
TREND_FEATURES = [
    "ask1_price_trend_60", "bid1_price_trend_60",
    "buy_spread_trend_60", "sell_spread_trend_60",
    "wap_1_trend_60", "wap_2_trend_60",
    "buy_vwap_trend_60", "sell_vwap_trend_60",
    "volume_trend_60"
]

# 所有因子列表
ALL_FEATURES = (
    KLINE_FEATURES +
    ["volume"] + SIZE_N_FEATURES +
    WAP_FEATURES +
    SPREAD_FEATURES +
    VOLUME_FEATURES +
    VWAP_FEATURES +
    LOG_RETURN_FEATURES +
    TREND_FEATURES
)

# ==================== 数据验证配置 ====================
# 数据质量检查开关
ENABLE_DATA_VALIDATION = True

# 验证规则
VALIDATION_RULES = {
    "check_null": True,           # 检查空值
    "check_spread": True,         # 检查价差是否为正
    "check_bid_ask": True,        # 检查买价 < 卖价
    "check_volume_imbalance": True,  # 检查成交量不平衡度在 [-1, 1]
    "check_inf": True,            # 检查无穷值
    "check_timestamp": True       # 检查时间戳连续性
}

# 异常值处理策略
OUTLIER_STRATEGY = "remove"  # 可选: "remove", "cap", "interpolate"

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"  # 可选: "DEBUG", "INFO", "WARNING", "ERROR"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / f"feature_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# ==================== 性能配置 ====================
# 显示进度条
SHOW_PROGRESS = True

# 保存中间结果
SAVE_INTERMEDIATE = False

# 中间结果保存路径
INTERMEDIATE_DIR = OUTPUT_ROOT / "intermediate"

# ==================== 辅助函数 ====================
def get_bookdepth_filepath(date_str: str) -> Path:
    """
    获取订单簿数据文件路径

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'

    Returns:
        Path: 完整文件路径
    """
    filename = BOOKDEPTH_FILENAME_TEMPLATE.format(
        symbol=SYMBOL,
        date=date_str
    )
    return BOOKDEPTH_BASE_PATH / filename


def get_kline_filepath(date_str: str) -> Path:
    """
    获取K线数据文件路径

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'

    Returns:
        Path: 完整文件路径
    """
    filename = KLINE_FILENAME_TEMPLATE.format(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        date=date_str
    )
    return KLINE_BASE_PATH / filename


def get_output_filepath(date_str: str = None, month_str: str = None,
                            start_date: str = None,
                        end_date: str = None,
                        ) -> Path:
    """
    获取输出文件路径

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD' (用于单文件输出)
        month_str: 月份字符串，格式 'YYYYMM' (用于按月输出)

    Returns:
        Path: 输出文件路径
    """
    FEATURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_STRATEGY == "monthly" and month_str:
        filename = f"features_{month_str}.{OUTPUT_FORMAT}"
    elif date_str:
        filename = f"features_{date_str.replace('-', '')}.{OUTPUT_FORMAT}"
    else:
        filename = f"features_{start_date.replace('-', '')}_{end_date.replace('-', '')}.{OUTPUT_FORMAT}"

    return FEATURES_OUTPUT_DIR / filename


def get_feature_columns():
    """
    获取所有因子列名

    Returns:
        List[str]: 所有因子列名列表
    """
    return ALL_FEATURES


def ensure_directories():
    """确保所有必要的目录存在"""
    FEATURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if SAVE_INTERMEDIATE:
        INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 初始化 ====================
if __name__ == "__main__":
    # 测试配置
    print("=" * 60)
    print("配置信息")
    print("=" * 60)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"数据根目录: {DATA_ROOT}")
    print(f"输出根目录: {OUTPUT_ROOT}")
    print(f"\n订单簿数据路径: {BOOKDEPTH_BASE_PATH}")
    print(f"K线数据路径: {KLINE_BASE_PATH}")
    print(f"\n交易对: {SYMBOL}")
    print(f"时间范围: {START_DATE} 至 {END_DATE}")
    print(f"\n输出策略: {OUTPUT_STRATEGY}")
    print(f"输出格式: {OUTPUT_FORMAT}")
    print(f"特征输出目录: {FEATURES_OUTPUT_DIR}")
    print(f"\n总因子数: {len(ALL_FEATURES)}")
    print("=" * 60)

    # 测试路径生成
    test_date = "2023-06-30"
    print(f"\n测试日期: {test_date}")
    print(f"订单簿文件: {get_bookdepth_filepath(test_date)}")
    print(f"K线文件: {get_kline_filepath(test_date)}")
    print(f"输出文件: {get_output_filepath(month_str='202306')}")
