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
# DCE数据基础路径
DCE_BASE_PATH = DATA_ROOT

# 品种配置
COMMODITY = "豆粕"  # 品种名称（中文）
SYMBOL = "m"  # 品种代码（豆粕）

# 数据类型
DATA_TYPE_LEVEL5 = "五档行情数据"  # 五档行情数据
DATA_TYPE_VOLUME = "期货成交量统计"  # 期货成交量统计
DATA_TYPE_ORDER = "十笔最优价位委托"  # 十笔最优价位委托

# ==================== 交易对配置 ====================
# 主力合约配置
USE_MAIN_CONTRACT = True  # 是否自动识别主力合约
MAIN_CONTRACT_CRITERIA = "OpenInterest"  # 主力合约判断标准: "OpenInterest" 或 "Volume"
DEFAULT_CONTRACT = None  # 默认合约（如果设置为None，则自动识别主力合约）
TIMEFRAME = "1m"  # 时间粒度

# ==================== 数据时间范围配置 ====================
START_DATE = "2023-09-01"
END_DATE = "2023-09-30"

# ==================== 文件命名模板 ====================
# DCE数据目录结构: data/豆粕/2023/01/20230103/五档行情数据/m2301.csv
# 路径模板: {base_path}/{commodity}/{year}/{month}/{YYYYMMDD}/{data_type}/{contract}.csv
DCE_DIR_TEMPLATE = "{commodity}/{year}/{month}/{year_month_day}/{data_type}"
DCE_FILENAME_TEMPLATE = "{contract}.csv"

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

# ==================== DCE五档行情数据列配置 ====================
# DCE五档行情原始列名
DCE_LEVEL5_COLUMNS = [
    "ActionDay", "TradingDay", "UpdateTime", "InstrumentID",
    "LastPrice", "HighPrice", "LowPrice", "OpenPrice", "ClosePrice",
    "LastVolume", "Volume", "Turnover", "OpenInterest", "PreOpenInterest",
    "OpenInteChange", "AveragePrice", "SettlementPrice", "PreSettlementPrice", "PreClosePrice",
    "BuyVolume", "SellVolume", "AvgBuyPrice", "AvgSellPrice",
    "BidPrice1", "BidVolume1", "DerBidVolume1",
    "BidPrice2", "BidVolume2", "DerBidVolume2",
    "BidPrice3", "BidVolume3", "DerBidVolume3",
    "BidPrice4", "BidVolume4", "DerBidVolume4",
    "BidPrice5", "BidVolume5", "DerBidVolume5",
    "AskPrice1", "AskVolume1", "DerAskVolume1",
    "AskPrice2", "AskVolume2", "DerAskVolume2",
    "AskPrice3", "AskVolume3", "DerAskVolume3",
    "AskPrice4", "AskVolume4", "DerAskVolume4",
    "AskPrice5", "AskVolume5", "DerAskVolume5",
    "UpperLimitPrice", "LowerLimitPrice", "LifeHighPrice", "LifeLowPrice"
]

# DCE字段重命名映射 (原始字段名 -> 目标字段名)
DCE_RENAME_MAP = {
    # K线价格字段
    "OpenPrice": "open_price",
    "HighPrice": "high_price",
    "LowPrice": "low_price",
    "ClosePrice": "close_price",
    # 买方五档
    "BidPrice1": "bid1_price",
    "BidVolume1": "bid1_size",
    "BidPrice2": "bid2_price",
    "BidVolume2": "bid2_size",
    "BidPrice3": "bid3_price",
    "BidVolume3": "bid3_size",
    "BidPrice4": "bid4_price",
    "BidVolume4": "bid4_size",
    "BidPrice5": "bid5_price",
    "BidVolume5": "bid5_size",
    # 卖方五档
    "AskPrice1": "ask1_price",
    "AskVolume1": "ask1_size",
    "AskPrice2": "ask2_price",
    "AskVolume2": "ask2_size",
    "AskPrice3": "ask3_price",
    "AskVolume3": "ask3_size",
    "AskPrice4": "ask4_price",
    "AskVolume4": "ask4_size",
    "AskPrice5": "ask5_price",
    "AskVolume5": "ask5_size",
}

# 保留的原始字段（用于调试或其他用途）
DCE_KEEP_ORIGINAL = [
    "TradingDay", "UpdateTime", "InstrumentID",
    "Volume", "Turnover", "OpenInterest"
]

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
def get_dce_filepath(date_str: str, contract: str = None,
                     data_type: str = DATA_TYPE_LEVEL5,
                     commodity: str = COMMODITY) -> Path:
    """
    获取DCE数据文件路径

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD' (例: '2023-01-03')
        contract: 合约代码 (例: 'm2301')，如果为None则需要使用get_main_contract获取
        data_type: 数据类型 (默认: '五档行情数据')
        commodity: 品种名称 (默认: 从配置读取)

    Returns:
        Path: 完整文件路径
        例: data/豆粕/2023/01/20230103/五档行情数据/m2301.csv

    Raises:
        ValueError: 如果日期格式不正确或合约为None
    """
    from datetime import datetime

    try:
        # 解析日期
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.strftime("%Y")  # 2023
        month = date_obj.strftime("%m")  # 01
        year_month_day = date_obj.strftime("%Y%m%d")  # 20230103
    except ValueError as e:
        raise ValueError(f"日期格式错误，应为 'YYYY-MM-DD': {date_str}") from e

    if contract is None:
        raise ValueError("合约代码不能为None，请先调用get_main_contract获取主力合约")

    # 构建目录路径: data/豆粕/2023/01/20230103/五档行情数据
    dir_path = DCE_BASE_PATH / commodity / year / month / year_month_day / data_type

    # 构建完整文件路径
    filename = DCE_FILENAME_TEMPLATE.format(contract=contract)
    filepath = dir_path / filename

    return filepath


def get_available_contracts(date_str: str, data_type: str = DATA_TYPE_LEVEL5,
                           commodity: str = COMMODITY) -> list:
    """
    获取指定日期可用的合约列表

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        data_type: 数据类型
        commodity: 品种名称

    Returns:
        list: 可用的合约代码列表
    """
    from datetime import datetime

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.strftime("%Y")  # 2023
        month = date_obj.strftime("%m")  # 01
        year_month_day = date_obj.strftime("%Y%m%d")  # 20230103
    except ValueError:
        return []

    # 构建目录路径: data/豆粕/2023/01/20230103/五档行情数据
    dir_path = DCE_BASE_PATH / commodity / year / month / year_month_day / data_type

    # 检查目录是否存在
    if not dir_path.exists():
        return []

    # 获取所有CSV文件
    csv_files = list(dir_path.glob("*.csv"))

    # 提取合约代码（去掉.csv后缀）
    contracts = [f.stem for f in csv_files]

    return sorted(contracts)


def get_main_contract(date_str: str, data_type: str = DATA_TYPE_LEVEL5,
                     commodity: str = COMMODITY,
                     criteria: str = MAIN_CONTRACT_CRITERIA) -> str:
    """
    获取指定日期的主力合约

    主力合约判断标准：
    - OpenInterest: 持仓量最大的合约
    - Volume: 成交量最大的合约

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        data_type: 数据类型
        commodity: 品种名称
        criteria: 判断标准 ("OpenInterest" 或 "Volume")

    Returns:
        str: 主力合约代码 (例: 'm2301')

    Raises:
        ValueError: 如果没有找到可用合约或无法读取数据
    """
    import polars as pl

    # 获取所有可用合约
    contracts = get_available_contracts(date_str, data_type, commodity)

    if not contracts:
        raise ValueError(f"日期 {date_str} 没有找到可用的合约")

    # 如果只有一个合约，直接返回
    if len(contracts) == 1:
        return contracts[0]

    # 读取每个合约的数据，找到持仓量或成交量最大的
    max_value = -1
    main_contract = None

    for contract in contracts:
        try:
            filepath = get_dce_filepath(date_str, contract, data_type, commodity)
            if not filepath.exists():
                continue

            # 读取CSV，只取第一行数据来判断
            df = pl.read_csv(filepath, n_rows=100)

            # 根据标准选择列
            if criteria == "OpenInterest" and "OpenInterest" in df.columns:
                value = df["OpenInterest"].max()
            elif criteria == "Volume" and "Volume" in df.columns:
                value = df["Volume"].max()
            else:
                # 如果指定的列不存在，尝试另一个
                if "OpenInterest" in df.columns:
                    value = df["OpenInterest"].max()
                elif "Volume" in df.columns:
                    value = df["Volume"].max()
                else:
                    continue

            if value is not None and value > max_value:
                max_value = value
                main_contract = contract

        except Exception as e:
            # 如果读取某个合约失败，跳过
            continue

    if main_contract is None:
        # 如果无法通过数据判断，返回第一个合约
        return contracts[0]

    return main_contract


def get_output_filepath(date_str: str = None, month_str: str = None,
                            start_date: str = None,
                        end_date: str = None,
                        ) -> Path:
    """
    获取输出文件路径

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD' (用于单文件输出)
        month_str: 月份字符串，格式 'YYYYMM' (用于按月输出)
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'

    Returns:
        Path: 输出文件路径
    """
    FEATURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_STRATEGY == "monthly" and month_str:
        filename = f"features_{month_str}.{OUTPUT_FORMAT}"
    elif month_str:
        filename = f"features_{month_str}.{OUTPUT_FORMAT}"
    elif date_str:
        filename = f"features_{date_str.replace('-', '')}.{OUTPUT_FORMAT}"
    elif start_date and end_date:
        filename = f"features_{start_date.replace('-', '')}_{end_date.replace('-', '')}.{OUTPUT_FORMAT}"
    else:
        # 默认文件名
        filename = f"features.{OUTPUT_FORMAT}"

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
    print(f"\nDCE数据路径: {DCE_BASE_PATH}")
    print(f"品种: {COMMODITY} ({SYMBOL})")
    print(f"数据类型: {DATA_TYPE_LEVEL5}, {DATA_TYPE_VOLUME}, {DATA_TYPE_ORDER}")
    print(f"\n主力合约配置:")
    print(f"  自动识别: {USE_MAIN_CONTRACT}")
    print(f"  判断标准: {MAIN_CONTRACT_CRITERIA}")
    print(f"时间范围: {START_DATE} 至 {END_DATE}")
    print(f"\n输出策略: {OUTPUT_STRATEGY}")
    print(f"输出格式: {OUTPUT_FORMAT}")
    print(f"特征输出目录: {FEATURES_OUTPUT_DIR}")
    print(f"\n总因子数: {len(ALL_FEATURES)}")
    print("=" * 60)

    # 测试路径生成
    test_date = "2023-01-03"
    print(f"\n测试日期: {test_date}")

    # 测试获取可用合约
    print(f"\n可用合约列表:")
    contracts = get_available_contracts(test_date, DATA_TYPE_LEVEL5)
    print(f"  {contracts}")

    # 测试获取主力合约
    if contracts:
        main_contract = get_main_contract(test_date, DATA_TYPE_LEVEL5)
        print(f"\n主力合约: {main_contract}")

        print(f"\n测试合约: {main_contract}")
        print(f"五档行情文件: {get_dce_filepath(test_date, main_contract, DATA_TYPE_LEVEL5)}")
        print(f"输出文件: {get_output_filepath(month_str='202301')}")
    else:
        print(f"警告: 日期 {test_date} 没有找到可用合约")
