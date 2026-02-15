"""
数据加载模块
负责从 DCE CSV 文件中读取五档行情数据，并进行预处理
"""

import polars as pl
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import logging

try:
    # 尝试相对导入（当作为包导入时）
    from .config import (
        get_dce_filepath,
        get_available_contracts,
        get_main_contracts,
        DEFAULT_CONTRACT,
        USE_MAIN_CONTRACT,
        DATA_TYPE_LEVEL5,
        DATA_TYPE_VOLUME,
        DCE_RENAME_MAP,
        DCE_VOLUME_RENAME_MAP,
        DCE_KEEP_ORIGINAL,
        SHOW_PROGRESS
    )
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from config import (
        get_dce_filepath,
        get_available_contracts,
        get_main_contracts,
        DEFAULT_CONTRACT,
        USE_MAIN_CONTRACT,
        DATA_TYPE_LEVEL5,
        DATA_TYPE_VOLUME,
        DCE_RENAME_MAP,
        DCE_VOLUME_RENAME_MAP,
        DCE_KEEP_ORIGINAL,
        SHOW_PROGRESS
    )

# 配置日志
logger = logging.getLogger(__name__)


def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """
    生成日期范围列表

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'

    Returns:
        日期字符串列表
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    date_list = []
    current = start
    while current < end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return date_list


def load_daily_dce_data(date_str: str, main_contracts: List[str]) -> Optional[pl.DataFrame]:
    """
    从 CSV 文件中读取单日DCE五档行情数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        main_contracts: 主力合约列表，例如 ['m2301', 'm2305']

    Returns:
        Polars DataFrame 或 None（如果文件不存在）

    DataFrame 格式:
        - timestamp: 时间戳 (TradingDay + UpdateTime)
        - open_price, high_price, low_price, close_price: K线价格
        - bid1_price ~ bid5_price: 买方五档价格
        - bid1_size ~ bid5_size: 买方五档数量
        - ask1_price ~ ask5_price: 卖方五档价格
        - ask1_size ~ ask5_size: 卖方五档数量
        - contract: 合约代码（当合并多个合约时）
        - 其他原始字段...
    """
    if not main_contracts:
        logger.error("main_contracts 参数不能为空")
        return None

    # 加载并合并所有合约的数据
    all_dfs = []

    for contract_code in main_contracts:
        csv_path = get_dce_filepath(date_str, contract_code, DATA_TYPE_LEVEL5)

        if not csv_path.exists():
            logger.warning(f"DCE数据文件不存在: {csv_path}")
            continue

        try:
            # 读取CSV文件
            df = pl.read_csv(csv_path)

            # 检查必要的列是否存在
            required_cols = ["TradingDay", "UpdateTime"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"合约 {contract_code} 缺少必要列 {missing_cols}: {csv_path}")
                continue

            # 添加合约代码列
            df = df.with_columns(pl.lit(contract_code).alias("contract"))
            
            # 添加合约月份列（提取合约代码中的月份部分，只保留月份数字1-12）
            # 合约格式如：m2301 -> 月份为1，i2405 -> 月份为5
            month_str = contract_code[1:]  # 去掉品种代码，保留月份部分
            month_num = int(month_str[-2:])  # 提取最后两位作为月份数字
            df = df.with_columns(pl.lit(month_num).alias("contract_month"))
            
            all_dfs.append(df)
            logger.debug(f"成功加载合约数据: {date_str}, 合约: {contract_code}, 行数: {len(df)}")

        except Exception as e:
            logger.error(f"读取合约数据失败 {date_str}, 合约 {contract_code}: {str(e)}")
            continue

    if not all_dfs:
        logger.error(f"日期 {date_str} 所有合约数据加载失败")
        return None

    # 合并所有合约的数据
    if len(all_dfs) == 1:
        result_df = all_dfs[0]
    else:
        # 使用 concat 合并多个DataFrame
        result_df = pl.concat(all_dfs)
        logger.info(f"成功合并 {len(all_dfs)} 个合约的数据，总行数: {len(result_df)}")

    return result_df
 


def load_daily_volume_data(date_str: str, main_contracts: List[str]) -> Optional[pl.DataFrame]:
    """
    从CSV文件中读取单日DCE期货成交量统计数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        main_contracts: 主力合约列表，例如 ['m2301', 'm2305']

    Returns:
        Polars DataFrame 或 None（如果文件不存在）

    DataFrame 格式:
        - timestamp: 时间戳 (TradingDay + UpdateTime)
        - price1 ~ price5: 最优5个价位
        - buy_open_vol1 ~ sell_close_vol5: 开仓/平仓成交量
        - contract: 合约代码
    """
    if not main_contracts:
        logger.error("main_contracts 参数不能为空")
        return None

    # 加载并合并所有合约的数据
    all_dfs = []

    for contract_code in main_contracts:
        csv_path = get_dce_filepath(date_str, contract_code, DATA_TYPE_VOLUME)

        if not csv_path.exists():
            logger.warning(f"期货成交量统计数据文件不存在: {csv_path}")
            continue

        try:
            # 读取CSV文件
            df = pl.read_csv(csv_path)

            # 检查必要的列是否存在
            required_cols = ["TradingDay", "UpdateTime", "Price1"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"合约 {contract_code} 缺少必要列 {missing_cols}: {csv_path}")
                continue

            # 添加合约代码列
            df = df.with_columns(pl.lit(contract_code).alias("contract"))

            all_dfs.append(df)
            logger.debug(f"成功加载期货成交量统计数据: {date_str}, 合约: {contract_code}, 行数: {len(df)}")

        except Exception as e:
            logger.error(f"读取期货成交量统计数据失败 {date_str}, 合约 {contract_code}: {str(e)}")
            continue

    if not all_dfs:
        logger.error(f"日期 {date_str} 所有合约的期货成交量统计数据加载失败")
        return None

    # 合并所有合约的数据
    if len(all_dfs) == 1:
        result_df = all_dfs[0]
    else:
        result_df = pl.concat(all_dfs)
        logger.info(f"成功合并 {len(all_dfs)} 个合约的期货成交量统计数据，总行数: {len(result_df)}")

    return result_df


def calculate_ohlcv_from_volume_data(df: pl.DataFrame, window: str = "1m") -> pl.DataFrame:
    """
    从期货成交量统计数据计算K线OHLCV数据

    根据文档1.4节，K线价格需要通过期货成交量统计数据计算：
    - open_price: 窗口内第一个 Price1
    - high_price: 窗口内所有 Price1-5 的最大值
    - low_price: 窗口内所有 Price1-5 的最小值
    - close_price: 窗口内最后一个 Price1
    - volume: 窗口内总成交量（所有开仓/平仓量之和）

    Args:
        df: 期货成交量统计原始数据
        window: 时间窗口，默认 "1m" (1分钟)

    Returns:
        包含OHLCV的数据框
    """
    logger.info(f"开始计算OHLCV数据（窗口: {window}）")

    # 1. 创建时间戳
    df = df.with_columns(
        pl.col("TradingDay").cast(pl.Utf8).str.strptime(pl.Date, "%Y%m%d").alias("trading_date")
    )

    df = df.with_columns(
        (pl.col("trading_date").cast(pl.Utf8) + " " + pl.col("UpdateTime").cast(pl.Utf8))
        .str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S%.f")
        .alias("timestamp")
    )

    # 2. 重命名列
    df = df.rename(DCE_VOLUME_RENAME_MAP)

    # 3. 过滤掉价格为0的数据（无效价位）
    # 创建一个表达式来计算所有有效价格的最大值和最小值
    df = df.with_columns([
        # 收集所有非零价格
        pl.concat_list([
            pl.when(pl.col("price1") > 0).then(pl.col("price1")),
            pl.when(pl.col("price2") > 0).then(pl.col("price2")),
            pl.when(pl.col("price3") > 0).then(pl.col("price3")),
            pl.when(pl.col("price4") > 0).then(pl.col("price4")),
            pl.when(pl.col("price5") > 0).then(pl.col("price5"))
        ]).list.drop_nulls().alias("valid_prices")
    ])

    # 4. 按时间窗口截断时间戳
    df = df.with_columns(
        pl.col("timestamp").dt.truncate(window).alias("minute")
    )

    # 5. 按分钟分组计算OHLCV
    ohlcv_df = df.group_by(["minute", "contract"]).agg([
        # Open: 窗口内第一个 price1
        pl.col("price1").filter(pl.col("price1") > 0).first().alias("open_price"),

        # High: 窗口内所有有效价格的最大值
        pl.col("valid_prices").flatten().max().alias("high_price"),

        # Low: 窗口内所有有效价格的最小值
        pl.col("valid_prices").flatten().min().alias("low_price"),

        # Close: 窗口内最后一个 price1
        pl.col("price1").filter(pl.col("price1") > 0).last().alias("close_price"),

        # Volume: 所有开仓/平仓量之和
        (
            pl.col("buy_open_vol1").sum() + pl.col("buy_close_vol1").sum() +
            pl.col("sell_open_vol1").sum() + pl.col("sell_close_vol1").sum() +
            pl.col("buy_open_vol2").sum() + pl.col("buy_close_vol2").sum() +
            pl.col("sell_open_vol2").sum() + pl.col("sell_close_vol2").sum() +
            pl.col("buy_open_vol3").sum() + pl.col("buy_close_vol3").sum() +
            pl.col("sell_open_vol3").sum() + pl.col("sell_close_vol3").sum() +
            pl.col("buy_open_vol4").sum() + pl.col("buy_close_vol4").sum() +
            pl.col("sell_open_vol4").sum() + pl.col("sell_close_vol4").sum() +
            pl.col("buy_open_vol5").sum() + pl.col("buy_close_vol5").sum() +
            pl.col("sell_open_vol5").sum() + pl.col("sell_close_vol5").sum()
        ).alias("trade_volume")
    ]).sort("minute")

    # 重命名minute为timestamp
    ohlcv_df = ohlcv_df.rename({"minute": "timestamp"})

    logger.info(f"OHLCV计算完成，生成 {len(ohlcv_df)} 条K线数据")

    return ohlcv_df


def preprocess_dce_data(df: pl.DataFrame) -> pl.DataFrame:
    """
    预处理DCE五档行情数据

    处理步骤:
    1. 创建时间戳 (TradingDay + UpdateTime)
    2. 重命名列 (BidPrice1 -> bid1_price, etc.)
    3. 选择需要的列

    Args:
        df: 原始DCE数据

    Returns:
        预处理后的数据
    """
    logger.info("开始预处理DCE数据")
    original_rows = len(df)

    # 1. 创建时间戳：TradingDay + UpdateTime
    # TradingDay格式: 20230901 (整数), UpdateTime格式: "21:00:00.850" (字符串)

    # 将TradingDay从整数转为字符串格式 YYYY-MM-DD
    df = df.with_columns(
        pl.col("TradingDay").cast(pl.Utf8).str.strptime(pl.Date, "%Y%m%d").alias("trading_date")
    )

    # 合并日期和时间字符串
    df = df.with_columns(
        (pl.col("trading_date").cast(pl.Utf8) + " " + pl.col("UpdateTime").cast(pl.Utf8))
        .str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S%.f")
        .alias("timestamp")
    )

    # 2. 重命名列
    df = df.rename(DCE_RENAME_MAP)

    # 2.5 确保数值列是正确的类型
    # 订单簿价格和数量列
    for i in range(1, 6):
        for side in ["bid", "ask"]:
            price_col = f"{side}{i}_price"
            size_col = f"{side}{i}_size"
            if price_col in df.columns:
                df = df.with_columns(pl.col(price_col).cast(pl.Float64))
            if size_col in df.columns:
                df = df.with_columns(pl.col(size_col).cast(pl.Int64))

    # 3. 选择需要的列
    # 基础列
    base_columns = ["timestamp", "contract_month", "contract"]  # 添加contract列用于合并

    # 订单簿列（已重命名）
    orderbook_columns = []
    for i in range(1, 6):
        orderbook_columns.extend([
            f"bid{i}_price", f"bid{i}_size",
            f"ask{i}_price", f"ask{i}_size"
        ])

    # 保留的原始列（用于调试）
    original_columns = [col for col in DCE_KEEP_ORIGINAL if col in df.columns]

    # 合并所有需要的列（不包含K线价格列，它们将从期货成交量统计数据计算）
    columns_to_keep = base_columns + orderbook_columns + original_columns

    # 检查哪些列存在
    available_columns = [col for col in columns_to_keep if col in df.columns]
    missing_columns = [col for col in columns_to_keep if col not in df.columns]

    if missing_columns:
        logger.warning(f"缺少以下列: {missing_columns}")

    df = df.select(available_columns)

    # 4. 按时间戳排序
    df = df.sort("timestamp")

    # 5. 去重：保留每分钟第一条数据
    # 首先截断timestamp到分钟级别（用于与OHLCV数据对齐）
    df = df.with_columns(
        pl.col("timestamp").dt.truncate("1m").alias("timestamp")
    )

    # 对每分钟分组，选择第一条（现在timestamp已经是分钟级别，所以group_by可以直接使用timestamp）
    df = (
        df
        .group_by(["timestamp", "contract"] if "contract" in df.columns else "timestamp")
        .first()
        .sort("timestamp")
    )

    final_rows = len(df)

    logger.info(f"DCE数据预处理完成，行数: {original_rows} -> {final_rows} (每分钟保留1条)")
    if original_rows > final_rows:
        logger.info(f"过滤掉同分钟的重复数据: {original_rows - final_rows} 行")

    return df


def merge_ohlcv_and_orderbook(
    ohlcv_df: pl.DataFrame,
    orderbook_df: pl.DataFrame,
    how: str = "inner"
) -> pl.DataFrame:
    """
    合并OHLCV数据和五档行情数据

    Args:
        ohlcv_df: OHLCV数据（从期货成交量统计计算）
        orderbook_df: 五档行情数据（预处理后）
        how: 合并方式，默认 "inner"（内连接）

    Returns:
        合并后的完整数据，包含OHLCV + 订单簿数据
    """
    logger.info("开始合并OHLCV和五档行情数据")

    # 确保两个DataFrame都有timestamp列
    if "timestamp" not in ohlcv_df.columns or "timestamp" not in orderbook_df.columns:
        raise ValueError("OHLCV和订单簿数据都必须包含timestamp列")

    # 按timestamp和contract合并
    if "contract" in ohlcv_df.columns and "contract" in orderbook_df.columns:
        merged_df = ohlcv_df.join(
            orderbook_df,
            on=["timestamp", "contract"],
            how=how
        )
    else:
        merged_df = ohlcv_df.join(
            orderbook_df,
            on="timestamp",
            how=how
        )

    logger.info(f"合并完成，行数: {len(merged_df)}")

    return merged_df


def process_dce_data(df: pl.DataFrame) -> pl.DataFrame:
    """
    处理DCE数据（预处理的封装）

    Args:
        df: 原始DCE数据

    Returns:
        处理后的数据，包含所有必要的列
    """
    # DCE数据已经包含K线和订单簿数据，只需要预处理即可
    return preprocess_dce_data(df)


def load_and_merge_daily_data(date_str: str, contract: str = None) -> Optional[pl.DataFrame]:
    """
    加载单日数据并合并OHLCV和五档行情

    根据文档1.4节，正确的数据处理流程：
    1. 确定当日主力合约（可能有多个）
    2. 从期货成交量统计数据计算OHLCV
    3. 从五档行情数据获取订单簿数据
    4. 按时间戳合并

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        contract: 合约代码，例如 'm2301'。如果为None且USE_MAIN_CONTRACT=True，则自动识别主力合约

    Returns:
        完整的数据框，包含OHLCV + 订单簿数据
    """
    logger.info(f"加载并合并日期 {date_str} 的数据")

    # 1. 确定要加载的合约列表
    contracts_to_load = []

    if contract is None:
        if USE_MAIN_CONTRACT:
            try:
                # 先从期货成交量统计数据识别主力合约
                contracts_to_load = get_main_contracts(date_str, DATA_TYPE_VOLUME)
                if not contracts_to_load:
                    logger.error(f"日期 {date_str} 未找到主力合约")
                    return None
                logger.info(f"日期 {date_str} 识别到主力合约: {contracts_to_load}")
            except ValueError as e:
                logger.error(f"无法识别主力合约: {str(e)}")
                return None
        elif DEFAULT_CONTRACT is not None:
            contracts_to_load = [DEFAULT_CONTRACT]
            logger.info(f"使用默认合约: {DEFAULT_CONTRACT}")
        else:
            logger.error("未指定合约代码，且未配置默认合约")
            return None
    elif isinstance(contract, str):
        contracts_to_load = [contract]
    elif isinstance(contract, list):
        contracts_to_load = contract
    else:
        logger.error(f"不支持的合约参数类型: {type(contract)}")
        return None

    # 2. 加载期货成交量统计数据并计算OHLCV（传入合约列表）
    volume_df = load_daily_volume_data(date_str, contracts_to_load)
    if volume_df is None:
        logger.warning(f"无法加载期货成交量统计数据: {date_str}")
        return None

    ohlcv_df = calculate_ohlcv_from_volume_data(volume_df)

    # 3. 加载五档行情数据（传入相同的合约列表）
    level5_df = load_daily_dce_data(date_str, contracts_to_load)
    if level5_df is None:
        logger.warning(f"无法加载五档行情数据: {date_str}")
        return None

    # 4. 预处理五档行情数据
    orderbook_df = preprocess_dce_data(level5_df)

    # 5. 合并OHLCV和订单簿数据
    merged_df = merge_ohlcv_and_orderbook(ohlcv_df, orderbook_df, how="inner")

    logger.info(f"日期 {date_str} 数据加载和合并完成，行数: {len(merged_df)}")

    return merged_df


def load_and_merge_date_range(
    start_date: str,
    end_date: str,
    contract: str = None,
    use_main_contract: bool = None
) -> Optional[pl.DataFrame]:
    """
    加载日期范围内的数据并合并OHLCV和五档行情

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        contract: 合约代码 (例: 'm2301')
        use_main_contract: 是否自动识别主力合约

    Returns:
        合并后的DataFrame
    """
    date_list = generate_date_range(start_date, end_date)
    logger.info(f"准备加载 {len(date_list)} 天的数据，从 {start_date} 到 {end_date}")

    # 确定是否使用主力合约
    if use_main_contract is None:
        use_main_contract = USE_MAIN_CONTRACT

    if contract is not None:
        logger.info(f"使用固定合约: {contract}")
    elif use_main_contract:
        logger.info("自动识别每日主力合约")
    elif DEFAULT_CONTRACT is not None:
        logger.info(f"使用默认合约: {DEFAULT_CONTRACT}")
        contract = DEFAULT_CONTRACT
    else:
        logger.error("未指定合约且未配置默认合约")
        return None

    all_dfs = []

    for i, date_str in enumerate(date_list):
        if SHOW_PROGRESS and (i + 1) % 10 == 0:
            logger.info(f"进度: {i + 1}/{len(date_list)} 天")

        # 如果使用主力合约且未指定固定合约，则每天识别
        daily_contract = contract if contract is not None else None

        # 加载并合并单日数据
        daily_df = load_and_merge_daily_data(date_str, daily_contract)
        if daily_df is not None:
            # 添加日期列用于调试
            daily_df = daily_df.with_columns(pl.lit(date_str).alias("date"))
            all_dfs.append(daily_df)

    # 合并所有日期的数据
    if not all_dfs:
        logger.warning("没有加载到任何数据")
        return None

    logger.info(f"合并 {len(all_dfs)} 天的数据")
    merged_df = pl.concat(all_dfs)
    logger.info(f"总行数: {len(merged_df)}")

    return merged_df


def validate_data(df: pl.DataFrame) -> bool:
    """
    验证数据质量

    检查项:
    1. 时间戳是否有空值
    2. 价格和数量是否有负值
    3. bid1_price < ask1_price
    4. 数据行数是否合理

    Args:
        df: 待验证的数据

    Returns:
        是否通过验证
    """
    logger.info("开始数据质量验证")

    passed = True

    # 检查空值
    if len(df) > 0:
        null_counts = df.null_count()
        # Polars 的 sum() 返回的是 DataFrame
        total_nulls_dict = null_counts.sum().to_dicts()[0]
        null_count = sum(total_nulls_dict.values())

        if null_count > 0:
            logger.warning(f"数据中存在 {null_count} 个空值")
            
            # 打印各列的空值数量
            for col, count in total_nulls_dict.items():
                if count > 0:
                    logger.warning(f"  列 '{col}': {count} 个空值")
            
            # 查找包含空值的具体行
            null_rows = df.filter(pl.any_horizontal(pl.all().is_null()))
            if len(null_rows) > 0:
                logger.warning(f"发现 {len(null_rows)} 行包含空值:")
                # 只显示前10行，避免日志过长
                for i, row in enumerate(null_rows.head(10).iter_rows(named=True)):
                    null_cols = [col for col, val in row.items() if val is None]
                    logger.warning(f"  第{i+1}行: 列 {null_cols} 包含空值")
                if len(null_rows) > 10:
                    logger.warning(f"  ... 还有 {len(null_rows) - 10} 行包含空值")
            # 不直接失败，因为某些列可能允许空值
    else:
        logger.warning("数据为空，跳过验证")
        return False

    # 检查 bid1_price < ask1_price
    if "bid1_price" in df.columns and "ask1_price" in df.columns:
        invalid_spread = df.filter(pl.col("bid1_price") >= pl.col("ask1_price"))
        if len(invalid_spread) > 0:
            logger.error(f"发现 {len(invalid_spread)} 行数据的 bid1_price >= ask1_price")
            passed = False

    # 检查负值（只检查数值类型的price列）
    price_columns = [col for col in df.columns if "price" in col and col in df.columns]
    for col in price_columns:
        # 跳过可能为负的特殊列
        if col in ["kmid", "ksft"]:
            continue
        # 只检查数值类型的列
        col_dtype = df[col].dtype
        if col_dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]:
            negative = df.filter(pl.col(col) < 0)
            if len(negative) > 0:
                logger.error(f"列 {col} 中存在 {len(negative)} 个负值")
                passed = False

    if passed:
        logger.info("数据质量验证通过")
    else:
        logger.warning("数据质量验证未通过")

    return passed


# ==================== 测试代码 ====================
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试单日数据加载和合并
    test_date = "2023-09-01"
    print(f"\n{'='*60}")
    print(f"测试加载并合并单日数据（OHLCV + 订单簿）")
    print(f"日期: {test_date}")
    print(f"{'='*60}")

    # 使用新的加载和合并函数
    merged_df = load_and_merge_daily_data(test_date)
    if merged_df is not None:
        print(f"\n合并后数据预览:")
        print(merged_df.head())
        print(f"形状: {merged_df.shape}")
        print(f"列名: {merged_df.columns}")

        # 检查OHLCV列是否存在
        ohlcv_cols = ["open_price", "high_price", "low_price", "close_price", "trade_volume"]
        missing_ohlcv = [col for col in ohlcv_cols if col not in merged_df.columns]
        if missing_ohlcv:
            print(f"\n警告: 缺少OHLCV列: {missing_ohlcv}")
        else:
            print(f"\n✓ OHLCV列已正确生成")
            print(f"\nOHLCV数据示例:")
            print(merged_df.select(["timestamp"] + ohlcv_cols).head())

        # 验证数据
        print(f"\n{'='*60}")
        print("数据质量验证")
        print(f"{'='*60}")
        validate_data(merged_df)

    # 测试日期范围加载和合并
    print(f"\n{'='*60}")
    print("测试日期范围数据加载和合并（自动识别主力合约）")
    print(f"{'='*60}")
    range_df = load_and_merge_date_range("2023-09-01", "2023-09-03")
    if range_df is not None:
        print(f"\n日期范围数据预览:")
        print(range_df.head())
        print(f"形状: {range_df.shape}")
        print(f"\nOHLCV数据示例:")
        print(range_df.select(["timestamp", "open_price", "high_price", "low_price", "close_price", "trade_volume"]).head())
        validate_data(range_df)