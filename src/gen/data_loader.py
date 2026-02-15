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
        get_main_contracts,
        DEFAULT_CONTRACT,
        USE_MAIN_CONTRACT,
        DATA_TYPE_VOLUME,
        SHOW_PROGRESS
    )
    # 从拆分的模块导入
    from .level5_loader import load_daily_dce_data, preprocess_dce_data
    from .volume_loader import load_daily_volume_data, calculate_ohlcv_from_volume_data
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from config import (
        get_main_contracts,
        DEFAULT_CONTRACT,
        USE_MAIN_CONTRACT,
        DATA_TYPE_VOLUME,
        SHOW_PROGRESS
    )
    # 从拆分的模块导入
    from level5_loader import load_daily_dce_data, preprocess_dce_data
    from volume_loader import load_daily_volume_data, calculate_ohlcv_from_volume_data

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

    # 记录合并前的行数
    ohlcv_rows = len(ohlcv_df)
    orderbook_rows = len(orderbook_df)
    logger.info(f"  OHLCV数据行数: {ohlcv_rows}")
    logger.info(f"  订单簿数据行数: {orderbook_rows}")

    # 确保两个DataFrame都有timestamp列
    if "timestamp" not in ohlcv_df.columns or "timestamp" not in orderbook_df.columns:
        raise ValueError("OHLCV和订单簿数据都必须包含timestamp列")

    # 按timestamp和contract合并
    if "contract" in ohlcv_df.columns and "contract" in orderbook_df.columns:
        join_keys = ["timestamp", "contract"]
        merged_df = ohlcv_df.join(
            orderbook_df,
            on=join_keys,
            how=how
        )
    else:
        join_keys = ["timestamp"]
        merged_df = ohlcv_df.join(
            orderbook_df,
            on=join_keys,
            how=how
        )

    merged_rows = len(merged_df)
    logger.info(f"  合并后行数: {merged_rows}")

    # 分析行数差异
    if how == "inner":
        ohlcv_lost = ohlcv_rows - merged_rows
        orderbook_lost = orderbook_rows - merged_rows

        if ohlcv_lost > 0 or orderbook_lost > 0:
            logger.warning(f"  数据差异分析:")
            if ohlcv_lost > 0:
                logger.warning(f"    OHLCV中有 {ohlcv_lost} 行在订单簿中找不到匹配 (丢失 {ohlcv_lost/ohlcv_rows*100:.1f}%)")
            if orderbook_lost > 0:
                logger.warning(f"    订单簿中有 {orderbook_lost} 行在OHLCV中找不到匹配 (丢失 {orderbook_lost/orderbook_rows*100:.1f}%)")

            # 找出不匹配的时间戳
            if "contract" in ohlcv_df.columns and "contract" in orderbook_df.columns:
                # 有合约列的情况
                ohlcv_keys = set(ohlcv_df.select(join_keys).iter_rows())
                orderbook_keys = set(orderbook_df.select(join_keys).iter_rows())
                only_in_ohlcv = ohlcv_keys - orderbook_keys
                only_in_orderbook = orderbook_keys - ohlcv_keys

                if only_in_ohlcv:
                    logger.warning(f"    仅在OHLCV中存在的时间点数量: {len(only_in_ohlcv)}")
                    # 显示前10个不匹配的时间点
                    sample_size = min(10, len(only_in_ohlcv))
                    logger.warning(f"    示例（前{sample_size}个）:")
                    for idx, key in enumerate(sorted(only_in_ohlcv)[:sample_size], 1):
                        logger.warning(f"      {idx}. timestamp={key[0]}, contract={key[1]}")

                if only_in_orderbook:
                    logger.warning(f"    仅在订单簿中存在的时间点数量: {len(only_in_orderbook)}")
                    # 显示前10个不匹配的时间点
                    sample_size = min(10, len(only_in_orderbook))
                    logger.warning(f"    示例（前{sample_size}个）:")
                    for idx, key in enumerate(sorted(only_in_orderbook)[:sample_size], 1):
                        logger.warning(f"      {idx}. timestamp={key[0]}, contract={key[1]}")
            else:
                # 没有合约列的情况
                ohlcv_timestamps = set(ohlcv_df.select("timestamp").to_series())
                orderbook_timestamps = set(orderbook_df.select("timestamp").to_series())
                only_in_ohlcv = ohlcv_timestamps - orderbook_timestamps
                only_in_orderbook = orderbook_timestamps - ohlcv_timestamps

                if only_in_ohlcv:
                    logger.warning(f"    仅在OHLCV中存在的时间点数量: {len(only_in_ohlcv)}")
                    sample_size = min(10, len(only_in_ohlcv))
                    logger.warning(f"    示例（前{sample_size}个）:")
                    for idx, ts in enumerate(sorted(only_in_ohlcv)[:sample_size], 1):
                        logger.warning(f"      {idx}. {ts}")

                if only_in_orderbook:
                    logger.warning(f"    仅在订单簿中存在的时间点数量: {len(only_in_orderbook)}")
                    sample_size = min(10, len(only_in_orderbook))
                    logger.warning(f"    示例（前{sample_size}个）:")
                    for idx, ts in enumerate(sorted(only_in_orderbook)[:sample_size], 1):
                        logger.warning(f"      {idx}. {ts}")
        else:
            logger.info(f"  ✓ 所有数据完美匹配，无数据丢失")

    return merged_df


 


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
    
    merged_dfs = []
    for contract in contracts_to_load:
        # 2. 加载期货成交量统计数据并计算OHLCV（传入合约列表）
        volume_df = load_daily_volume_data(date_str, contract)
        if volume_df is None:
            logger.warning(f"无法加载期货成交量统计数据: {date_str}")
            return None

        ohlcv_df = calculate_ohlcv_from_volume_data(volume_df)
        
        # 3. 加载五档行情数据（传入相同的合约列表）
        level5_df = load_daily_dce_data(date_str, contract)
        if level5_df is None:
            logger.warning(f"无法加载五档行情数据: {date_str}")
            return None

        # 4. 预处理五档行情数据
        orderbook_df = preprocess_dce_data(level5_df)

        # 5. 合并OHLCV和订单簿数据
        merged_df = merge_ohlcv_and_orderbook(ohlcv_df, orderbook_df, how="inner")

        logger.info(f"日期 {date_str} 数据加载和合并完成，行数: {len(merged_df)}")
        merged_dfs.append(merged_df)
    return pl.concat(merged_dfs)


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
        print(range_df.select(["timestamp", "open_price", "high_price", "low_price", "close_price", "trade_volume1", "trade_volume2"]).head())
        validate_data(range_df)