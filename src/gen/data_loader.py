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
        DCE_RENAME_MAP,
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
        DCE_RENAME_MAP,
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


def load_daily_dce_data(date_str: str, contract: str = None) -> Optional[pl.DataFrame]:
    """
    从 CSV 文件中读取单日DCE五档行情数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        contract: 合约代码，例如 'm2301'。如果为None且USE_MAIN_CONTRACT=True，则自动识别主力合约
                  如果传入合约列表，则加载并合并所有合约的数据

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
    contracts_to_load = []
    
    # 确定要加载的合约列表
    if contract is None:
        if USE_MAIN_CONTRACT:
            try:
                contracts_to_load = get_main_contracts(date_str, DATA_TYPE_LEVEL5)
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

    # 加载并合并所有合约的数据
    all_dfs = []
    
    for contract_code in contracts_to_load:
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


def load_date_range_data(
    start_date: str,
    end_date: str,
    contract: str = None,
    use_main_contract: bool = None
) -> Optional[pl.DataFrame]:
    """
    加载日期范围内的所有DCE数据

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        contract: 合约代码 (例: 'm2301')。如果为None，根据use_main_contract参数决定行为
        use_main_contract: 是否自动识别主力合约。如果为None，使用配置文件中的USE_MAIN_CONTRACT

    Returns:
        合并后的DataFrame 或 None

    说明:
        - 如果指定了contract参数，则所有日期使用同一合约
        - 如果contract为None且use_main_contract=True，则每天自动识别当天的主力合约
        - 如果contract为None且use_main_contract=False，使用DEFAULT_CONTRACT
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

    dce_dfs = []

    for i, date_str in enumerate(date_list):
        if SHOW_PROGRESS and (i + 1) % 10 == 0:
            logger.info(f"进度: {i + 1}/{len(date_list)} 天")

        # 如果使用主力合约且未指定固定合约，则每天识别
        daily_contract = contract if contract is not None else None

        # 加载DCE数据
        dce_df = load_daily_dce_data(date_str, daily_contract)
        if dce_df is not None:
            # 添加日期列用于调试
            dce_df = dce_df.with_columns(pl.lit(date_str).alias("date"))
            dce_dfs.append(dce_df)

    # 合并所有日期的数据
    if not dce_dfs:
        logger.warning("没有加载到任何数据")
        return None

    logger.info(f"合并 {len(dce_dfs)} 天的DCE数据")
    merged_df = pl.concat(dce_dfs)
    logger.info(f"总行数: {len(merged_df)}")

    return merged_df


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
    # K线价格列
    price_cols = ["open_price", "high_price", "low_price", "close_price"]
    for col in price_cols:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Float64))

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
    base_columns = ["timestamp","contract_month"]

    # K线价格列（已重命名）
    kline_columns = ["open_price", "high_price", "low_price", "close_price"]

    # 订单簿列（已重命名）
    orderbook_columns = []
    for i in range(1, 6):
        orderbook_columns.extend([
            f"bid{i}_price", f"bid{i}_size",
            f"ask{i}_price", f"ask{i}_size"
        ])

    # 保留的原始列（用于调试）
    original_columns = [col for col in DCE_KEEP_ORIGINAL if col in df.columns]

    # 合并所有需要的列
    columns_to_keep = base_columns + kline_columns + orderbook_columns + original_columns

    # 检查哪些列存在
    available_columns = [col for col in columns_to_keep if col in df.columns]
    missing_columns = [col for col in columns_to_keep if col not in df.columns]

    if missing_columns:
        logger.warning(f"缺少以下列: {missing_columns}")

    df = df.select(available_columns)

    # 4. 按时间戳排序
    df = df.sort("timestamp")

    # 5. 去重：保留每分钟第一条数据
    # 添加辅助列：分钟级别的时间戳
    df = df.with_columns(
        pl.col("timestamp").dt.truncate("1m").alias("minute")
    )

    # 对每分钟分组，选择第一条
    df = (
        df
        .group_by("minute")
        .first()
        .drop("minute")
        .sort("timestamp")
    )

    final_rows = len(df)

    logger.info(f"DCE数据预处理完成，行数: {original_rows} -> {final_rows} (每分钟保留1条)")
    if original_rows > final_rows:
        logger.info(f"过滤掉同分钟的重复数据: {original_rows - final_rows} 行")

    return df


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

    # 测试单日数据加载
    test_date = "2023-01-03"
    print(f"\n{'='*60}")
    print(f"测试加载单日DCE数据（自动识别主力合约）")
    print(f"日期: {test_date}")
    print(f"{'='*60}")

    # 加载DCE数据（自动识别主力合约）
    dce_df = load_daily_dce_data(test_date)
    if dce_df is not None:
        print(f"\nDCE原始数据预览:")
        print(dce_df.head())
        print(f"形状: {dce_df.shape}")
        print(f"列名: {dce_df.columns}")

        # 测试预处理
        print(f"\n{'='*60}")
        print("测试DCE数据预处理")
        print(f"{'='*60}")
        processed = preprocess_dce_data(dce_df)
        print(f"\n预处理后数据预览:")
        print(processed.head())
        print(f"形状: {processed.shape}")
        print(f"列名: {processed.columns}")

        # 验证数据
        print(f"\n{'='*60}")
        print("数据质量验证")
        print(f"{'='*60}")
        validate_data(processed)

    # 测试日期范围加载
    print(f"\n{'='*60}")
    print("测试日期范围数据加载（自动识别主力合约）")
    print(f"{'='*60}")
    range_df = load_date_range_data("2023-01-03", "2023-01-05")
    if range_df is not None:
        print(f"\n日期范围数据预览:")
        print(range_df.head())
        print(f"形状: {range_df.shape}")

        # 预处理
        processed_range = preprocess_dce_data(range_df)
        print(f"\n预处理后形状: {processed_range.shape}")
        validate_data(processed_range)