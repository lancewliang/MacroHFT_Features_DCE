"""
配置文件
包含所有数据路径、参数和常量配置
"""

from pathlib import Path
from datetime import datetime

ROLLING_WINDOWS = [60, 180, 360]

# ==================== 项目路径配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUT_ROOT = PROJECT_ROOT / "output"

# ==================== 数据源配置 ====================
# DCE数据基础路径
DCE_BASE_PATH = DATA_ROOT

# 品种配置
COMMODITY = "铝"  # 品种名称（中文）
SYMBOL = "al"  # 品种代码（铝）

# 数据类型
DATA_TYPE_LEVEL5 = "五档行情数据"  # 五档行情数据
DATA_TYPE_VOLUME = "期货成交量统计"  # 期货成交量统计
DATA_TYPE_ORDER = "十笔最优价位委托"  # 十笔最优价位委托

# ==================== 品种主力合约月份配置 ====================
# 各品种的主力合约月份（根据交易所规则配置）
MAIN_CONTRACT_MONTHS = {
    "豆粕": [1, 5, 9],      # 豆粕主力月份：1月、5月、9月
    "m": [1, 5, 9],         # 豆粕代码别名
    "豆油": [1, 5, 9],      # 豆油主力月份：1月、5月、9月
    "y": [1, 5, 9],         # 豆油代码别名
    "玉米": [1, 5, 9],      # 玉米主力月份：1月、5月、9月
    "c": [1, 5, 9],         # 玉米代码别名
    "豆一": [1, 3, 5, 7, 9, 11],  # 豆一主力月份
    "a": [1, 3, 5, 7, 9, 11],     # 豆一代码别名
    "豆二": [1, 3, 5, 7, 9, 11],  # 豆二主力月份
    "b": [1, 3, 5, 7, 9, 11],     # 豆二代码别名
    "棕榈油": [1, 5, 9],    # 棕榈油主力月份
    "p": [1, 5, 9],         # 棕榈油代码别名
}

# ==================== 交易对配置 ====================
# 主力合约配置
USE_MAIN_CONTRACT = True  # 是否自动识别主力合约
MAIN_CONTRACT_CRITERIA = "config"  # 主力合约判断标准: "config"(配置文件)
DEFAULT_CONTRACT = None  # 默认合约（如果设置为None，则自动识别主力合约）
TIMEFRAME = "1m"  # 时间粒度

# ==================== 数据时间范围配置 ====================
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"

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

# orderbook 聚合 CSV 基础列
ORDERBOOK_BASE_COLUMNS = [
    "datetime",
    "minute",
    "is_consecutive_minute",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "total_trade_volume",
    "turnover",
    "open_interest",
]

ORDERBOOK_LEVEL_COLUMNS = [
    *[f"bid{i}_price" for i in range(1, 6)],
    *[f"bid{i}_size" for i in range(1, 6)],
    *[f"ask{i}_price" for i in range(1, 6)],
    *[f"ask{i}_size" for i in range(1, 6)],
]

ORDERBOOK_REQUIRED_COLUMNS = ORDERBOOK_BASE_COLUMNS + ORDERBOOK_LEVEL_COLUMNS

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
# 注意：K线价格字段(open_price, high_price, low_price, close_price)
# 需要从期货成交量统计数据计算，不从五档行情直接映射
DCE_RENAME_MAP = {
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
    # 成交量和成交额（快照数据）
    "Volume": "volume_snp",
    "Turnover": "turnover_snp",
}

# 期货成交量统计数据字段重命名映射（用于OHLCV计算）
DCE_VOLUME_RENAME_MAP = {
    "Price1": "price1",
    "Price2": "price2",
    "Price3": "price3",
    "Price4": "price4",
    "Price5": "price5",
    "BuyOpenVol1": "buy_open_vol1",
    "BuyCloseVol1": "buy_close_vol1",
    "SellOpenVol1": "sell_open_vol1",
    "SellCloseVol1": "sell_close_vol1",
    "BuyOpenVol2": "buy_open_vol2",
    "BuyCloseVol2": "buy_close_vol2",
    "SellOpenVol2": "sell_open_vol2",
    "SellCloseVol2": "sell_close_vol2",
    "BuyOpenVol3": "buy_open_vol3",
    "BuyCloseVol3": "buy_close_vol3",
    "SellOpenVol3": "sell_open_vol3",
    "SellCloseVol3": "sell_close_vol3",
    "BuyOpenVol4": "buy_open_vol4",
    "BuyCloseVol4": "buy_close_vol4",
    "SellOpenVol4": "sell_open_vol4",
    "SellCloseVol4": "sell_close_vol4",
    "BuyOpenVol5": "buy_open_vol5",
    "BuyCloseVol5": "buy_close_vol5",
    "SellOpenVol5": "sell_open_vol5",
    "SellCloseVol5": "sell_close_vol5",
}

# 保留的原始字段（用于调试或其他用途）
# 注意：Volume 和 Turnover 已通过 DCE_RENAME_MAP 重命名为 volume_snp 和 turnover_snp
# 它们在 level5_loader.py 中通过 snapshot_columns 显式处理
DCE_KEEP_ORIGINAL = [
    "TradingDay", "UpdateTime", "InstrumentID",
    "OpenInterest"
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

# 分层不平衡与队列集中度因子
DEPTH_BALANCE_FEATURES = [
    "imbalance_top1", "imbalance_top3", "imbalance_top5",
    "weighted_imbalance_inv",
    "bid1_queue_concentration", "ask1_queue_concentration",
    "top2_depth_share",
]

# 成交与持仓快照衍生因子
TRADE_SNAPSHOT_FEATURES = [
    "trade_volume_delta", "turnover_delta",
    "avg_trade_price", "avg_trade_price_bias",
    "avg_trade_price_bias_change",
    "open_interest_change", "open_interest_change_ratio",
    "open_interest_change_per_trade",
]

# VWAP 因子
VWAP_FEATURES = ["buy_vwap", "sell_vwap"]

# 对数收益率因子
LOG_RETURN_FEATURES = [
    "log_return_bid1_price", "log_return_bid2_price",
    "log_return_ask1_price", "log_return_ask2_price",
    "log_return_wap_1", "log_return_wap_2"
]

# 稳定性因子
STABILITY_FEATURES = [
    "best_spread_duration", "best_quote_duration",
    *[f"log_return_wap_1_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"log_return_wap_2_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"log_return_bid1_price_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"price_spread_vol_{window}" for window in ROLLING_WINDOWS],
]

# 订单流失衡因子
ORDER_FLOW_FEATURES = [
    "ofi",
    *[f"ofi_{window}" for window in ROLLING_WINDOWS],
    *[f"ofi_vol_{window}" for window in ROLLING_WINDOWS],
]

# 盘口形状因子
BOOK_SHAPE_FEATURES = [
    "bid_depth_slope", "ask_depth_slope",
    "bid_book_convexity", "ask_book_convexity"
]

# 动态盘口微观结构因子
DYNAMIC_MICROSTRUCTURE_FEATURES = [
    "imbalance_top3_change", "weighted_imbalance_inv_change",
    *[f"ofi_zscore_{window}" for window in ROLLING_WINDOWS],
    "bid_depth_slope_change", "ask_depth_slope_change",
]

# 成交与持仓滚动因子
TRADE_ROLLING_FEATURES = [
    *[f"trade_volume_delta_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"turnover_delta_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"avg_trade_price_bias_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"open_interest_change_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"trade_volume_delta_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"turnover_delta_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"avg_trade_price_bias_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"open_interest_change_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"signed_trade_pressure_{window}" for window in ROLLING_WINDOWS],
    *[f"signed_open_interest_pressure_{window}" for window in ROLLING_WINDOWS],
    *[f"trade_ofi_resonance_{window}" for window in ROLLING_WINDOWS],
    *[f"trade_volume_delta_slope_{window}" for window in ROLLING_WINDOWS],
    *[f"turnover_delta_slope_{window}" for window in ROLLING_WINDOWS],
    *[f"avg_trade_price_bias_slope_{window}" for window in ROLLING_WINDOWS],
    *[f"open_interest_slope_{window}" for window in ROLLING_WINDOWS],
]

# 趋势因子
TREND_BASE_COLUMNS = [
    "ask1_price", "bid1_price",
    "buy_spread", "sell_spread",
    "wap_1", "wap_2",
    "buy_vwap", "sell_vwap",
    "volume",
]
TREND_FEATURES = [
    f"{col}_trend_{window}"
    for window in ROLLING_WINDOWS
    for col in TREND_BASE_COLUMNS
]

# 所有因子列表
ALL_FEATURES = (
    KLINE_FEATURES +
    ["volume"] + SIZE_N_FEATURES +
    WAP_FEATURES +
    SPREAD_FEATURES +
    VOLUME_FEATURES +
    DEPTH_BALANCE_FEATURES +
    TRADE_SNAPSHOT_FEATURES +
    VWAP_FEATURES +
    LOG_RETURN_FEATURES +
    STABILITY_FEATURES +
    ORDER_FLOW_FEATURES +
    BOOK_SHAPE_FEATURES +
    DYNAMIC_MICROSTRUCTURE_FEATURES +
    TRADE_ROLLING_FEATURES +
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
        contract: 合约代码 (例: 'm2301')，如果为None则需要使用get_main_contracts获取
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
        raise ValueError("合约代码不能为None，请先调用get_main_contracts获取主力合约")

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


def get_main_contracts(date_str: str, data_type: str = DATA_TYPE_LEVEL5,
                     commodity: str = COMMODITY,
                     volume_threshold: float = 0.5
                    ) -> list:
    """
    获取指定日期的主力合约列表
   
    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        data_type: 数据类型
        commodity: 品种名称
        volume_threshold: 成交量阈值，成交量达到最大成交量该比例的合约都视为主力合约 (默认: 0.8)

    Returns:
        list: 主力合约代码列表 (例: ['m2301', 'm2305'])

    Raises:
        ValueError: 如果没有找到可用合约或无法读取数据
    """
    import polars as pl

    # 获取所有可用合约
    contracts = get_available_contracts(date_str, data_type, commodity)
    
    if not contracts:
        raise ValueError(f"日期 {date_str} 没有找到可用合约")
    
    # 获取品种的主力月份配置
    main_months = MAIN_CONTRACT_MONTHS.get(commodity, [])
    if not main_months:
        # 如果没有配置，使用品种代码别名
        symbol = SYMBOL if commodity == COMMODITY else commodity
        main_months = MAIN_CONTRACT_MONTHS.get(symbol, [])
    
    if not main_months:
        raise ValueError(f"品种 {commodity} 没有配置主力月份")
    
    # 筛选符合主力月份的合约
    main_month_contracts = []
    for contract in contracts:
        if len(contract) >= 4:
            # 提取合约月份（最后两位数字）
            try:
                month = int(contract[-2:])
                if month in main_months:
                    main_month_contracts.append(contract)
            except ValueError:
                continue
    
    if not main_month_contracts:
        raise ValueError(f"日期 {date_str} 没有找到符合主力月份的合约")
    
    # 收集所有合约的成交量信息
    contract_volumes = {}

    for contract in main_month_contracts:
        try:
            # 读取合约数据
            filepath = get_dce_filepath(date_str, contract, data_type, commodity)
            if filepath.exists():
                df = pl.read_csv(filepath)

                # 根据数据类型计算当日总成交量
                if data_type == DATA_TYPE_VOLUME:
                    # 期货成交量统计数据：累加所有开仓/平仓量
                    vol_cols = []
                    for i in range(1, 6):
                        for prefix in ["BuyOpenVol", "BuyCloseVol", "SellOpenVol", "SellCloseVol"]:
                            col_name = f"{prefix}{i}"
                            if col_name in df.columns:
                                vol_cols.append(col_name)

                    if vol_cols:
                        total_volume = sum(df[col].sum() for col in vol_cols)
                    else:
                        total_volume = 0

                elif "Volume" in df.columns:
                    # 五档行情数据：使用Volume字段的变化量
                    total_volume = df["Volume"].max() - df["Volume"].min()
                elif "volume" in df.columns:
                    total_volume = df["volume"].max() - df["volume"].min()
                else:
                    # 如果没有成交量字段，使用持仓量变化
                    if "OpenInterest" in df.columns:
                        total_volume = df["OpenInterest"].max() - df["OpenInterest"].min()
                    else:
                        total_volume = 0

                contract_volumes[contract] = total_volume
        except Exception as e:
            # 如果某个合约读取失败，记录为0成交量
            contract_volumes[contract] = 0
            continue
    
    if not contract_volumes:
        raise ValueError(f"无法读取日期 {date_str} 的任何合约数据")
    
    # 找到最大成交量
    max_volume = max(contract_volumes.values())

    if max_volume == 0:
        raise ValueError(f"日期 {date_str} 的所有合约成交量都为0")

    # 计算阈值
    threshold_volume = max_volume * volume_threshold

    # 根据阈值确定主力合约列表
    main_contracts = []
    for contract, volume in contract_volumes.items():
        if volume >= threshold_volume:
            main_contracts.append(contract)

    # 按成交量降序排序
    main_contracts.sort(key=lambda x: contract_volumes[x], reverse=True)

    # 记录详细的识别信息
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"主力合约识别详情 ({date_str}):")
    logger.info(f"  符合主力月份的合约: {main_month_contracts}")
    logger.info(f"  成交量阈值: {volume_threshold:.1%} × 最大成交量 = {threshold_volume:,.0f}")
    logger.info(f"  各合约成交量:")

    # 按成交量降序显示所有合约
    sorted_contracts = sorted(contract_volumes.items(), key=lambda x: x[1], reverse=True)
    for contract, volume in sorted_contracts:
        percentage = (volume / max_volume * 100) if max_volume > 0 else 0
        is_main = "✓ 主力" if contract in main_contracts else "  "
        logger.info(f"    {is_main} {contract}: {volume:>12,.0f} ({percentage:>5.1f}%)")

    logger.info(f"  识别出主力合约: {main_contracts}")

    return main_contracts
 


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

    if OUTPUT_STRATEGY == "monthly" and month_str:
        filename = f"features_{month_str}{tf_suffix}.{OUTPUT_FORMAT}"
    elif month_str:
        filename = f"features_{month_str}{tf_suffix}.{OUTPUT_FORMAT}"
    elif date_str:
        filename = f"features_{date_str.replace('-', '')}{tf_suffix}.{OUTPUT_FORMAT}"
    elif start_date and end_date:
        filename = f"features_{start_date.replace('-', '')}_{end_date.replace('-', '')}{tf_suffix}.{OUTPUT_FORMAT}"
    else:
        filename = f"features{tf_suffix}.{OUTPUT_FORMAT}"

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
        # 显示主力月份配置
        main_months = MAIN_CONTRACT_MONTHS.get(COMMODITY)
        print(f"\n{COMMODITY} 主力月份配置: {main_months}")

        # 筛选符合主力月份的合约
        main_month_contracts = []
        for contract in contracts:
            if len(contract) >= 4:
                month = int(contract[-2:])
                if month in main_months:
                    main_month_contracts.append(contract)
        print(f"符合主力月份的合约: {main_month_contracts}")

        main_contract = get_main_contracts(test_date, DATA_TYPE_LEVEL5)
        print(f"\n识别的主力合约: {main_contract}")

        print(f"\n测试合约: {main_contract}")
        print(f"五档行情文件: {get_dce_filepath(test_date, main_contract, DATA_TYPE_LEVEL5)}")
        print(f"输出文件: {get_output_filepath(month_str='202301')}")
    else:
        print(f"警告: 日期 {test_date} 没有找到可用合约")
