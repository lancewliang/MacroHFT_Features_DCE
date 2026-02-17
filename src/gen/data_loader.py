"""
数据加载模块
负责从 DCE CSV 文件中读取五档行情数据，并进行预处理
"""

import polars as pl
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import logging

try:
    # 尝试相对导入（当作为包导入时）
    from .config import (
        SHOW_PROGRESS,
        DCE_BASE_PATH,
        COMMODITY,
    )
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from config import (
        SHOW_PROGRESS,
        DCE_BASE_PATH,
        COMMODITY,
    )

# 配置日志
logger = logging.getLogger(__name__)


def get_orderbook_filepath(date_str: str, contract: str, commodity: str = COMMODITY) -> Path:
    """
    获取 orderbook 数据文件路径

    目录结构: data/品种/年份/orderbook/合约-年-月-日_30s.csv

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD' (例: '2023-01-03')
        contract: 合约代码 (例: 'm2305')
        commodity: 品种名称 (默认: 从配置读取)

    Returns:
        Path: 完整文件路径
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.strftime("%Y")
    except ValueError as e:
        raise ValueError(f"日期格式错误，应为 'YYYY-MM-DD': {date_str}") from e

    if contract is None:
        raise ValueError("合约代码不能为None")

    dir_path = DCE_BASE_PATH / commodity / year / "orderbook"
    filename = f"{contract}-{date_str}_30s.csv"
    return dir_path / filename


def find_daily_contract(date_str: str, commodity: str = COMMODITY) -> Optional[str]:
    """
    自动识别指定日期的合约代码（每天只有1份合约文件）

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        commodity: 品种名称

    Returns:
        合约代码，未找到返回 None
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.strftime("%Y")
    except ValueError:
        return None

    dir_path = DCE_BASE_PATH / commodity / year / "orderbook"
    if not dir_path.exists():
        return None

    csv_files = list(dir_path.glob(f"*-{date_str}_30s.csv"))
    if not csv_files:
        return None

    # 从文件名提取合约代码：m2305-2023-01-03_30s.csv -> m2305
    return csv_files[0].stem.split('-')[0]


def load_daily_orderbook_data(date_str: str, contract: str = None) -> Optional[pl.DataFrame]:
    """
    加载单日 orderbook 数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        contract: 合约代码 (例: 'm2305')，如果为None则自动从目录识别

    Returns:
        包含 orderbook 数据的 DataFrame
    """
    logger.info(f"加载日期 {date_str} 的 orderbook 数据")

    if contract is None:
        contract = find_daily_contract(date_str)
        if contract is None:
            logger.error(f"日期 {date_str} 未找到合约文件")
            return None
        logger.info(f"自动识别合约: {contract}")

    filepath = get_orderbook_filepath(date_str, contract)
    if not filepath.exists():
        logger.warning(f"文件不存在: {filepath}")
        return None

    try:
        df = pl.read_csv(filepath)
        df = df.with_columns(pl.lit(contract).alias("contract"))

        if "datetime" in df.columns:
            df = df.with_columns(
                pl.col("datetime").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f").alias("timestamp")
            )

        logger.info(f"成功加载 {contract} 数据，行数: {len(df)}")
        return df

    except Exception as e:
        logger.error(f"加载文件失败 {filepath}: {str(e)}")
        return None


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


def load_and_merge_date_range(
    start_date: str,
    end_date: str,
    contract: str = None,
) -> Optional[pl.DataFrame]:
    """
    加载日期范围内的 orderbook 数据

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        contract: 合约代码，如果为None则每天自动识别

    Returns:
        合并后的 DataFrame
    """
    date_list = generate_date_range(start_date, end_date)
    logger.info(f"准备加载 {len(date_list)} 天的数据，从 {start_date} 到 {end_date}")

    if contract is not None:
        logger.info(f"使用固定合约: {contract}")

    all_dfs = []
    for i, date_str in enumerate(date_list):
        if SHOW_PROGRESS and (i + 1) % 10 == 0:
            logger.info(f"进度: {i + 1}/{len(date_list)} 天")

        daily_df = load_daily_orderbook_data(date_str, contract)
        if daily_df is not None:
            daily_df = daily_df.with_columns(pl.lit(date_str).alias("date"))
            all_dfs.append(daily_df)

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
    2. 价格列是否有负值
    3. bid1_price < ask1_price
    4. 数据行数是否合理

    Args:
        df: 待验证的数据

    Returns:
        是否通过验证
    """
    logger.info("开始数据质量验证")

    passed = True

    if len(df) == 0:
        logger.warning("数据为空，跳过验证")
        return False

    # 检查空值
    null_counts = df.null_count()
    total_nulls_dict = null_counts.sum().to_dicts()[0]
    null_count = sum(total_nulls_dict.values())

    if null_count > 0:
        logger.warning(f"数据中存在 {null_count} 个空值")
        for col, count in total_nulls_dict.items():
            if count > 0:
                logger.warning(f"  列 '{col}': {count} 个空值")

        null_rows = df.filter(pl.any_horizontal(pl.all().is_null()))
        if len(null_rows) > 0:
            logger.warning(f"发现 {len(null_rows)} 行包含空值:")
            for i, row in enumerate(null_rows.head(10).iter_rows(named=True)):
                null_cols = [col for col, val in row.items() if val is None]
                logger.warning(f"  第{i+1}行: 列 {null_cols} 包含空值")
            if len(null_rows) > 10:
                logger.warning(f"  ... 还有 {len(null_rows) - 10} 行包含空值")

    # 检查 bid1_price < ask1_price
    if "bid1_price" in df.columns and "ask1_price" in df.columns:
        invalid_spread = df.filter(pl.col("bid1_price") >= pl.col("ask1_price"))
        if len(invalid_spread) > 0:
            logger.error(f"发现 {len(invalid_spread)} 行数据的 bid1_price >= ask1_price")
            passed = False

    # 检查价格列负值
    price_columns = [col for col in df.columns if "price" in col]
    for col in price_columns:
        if col in ["kmid", "ksft"]:
            continue
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test_date = "2023-01-03"
    print(f"\n{'='*60}")
    print(f"测试加载单日 orderbook 数据")
    print(f"日期: {test_date}")
    print(f"{'='*60}")

    df = load_daily_orderbook_data(test_date)
    if df is not None:
        print(f"\n数据预览:")
        print(df.head())
        print(f"形状: {df.shape}")
        print(f"列名: {df.columns}")

        key_cols = ["timestamp", "open_price", "high_price", "low_price", "close_price",
                   "bid1_price", "bid1_size", "ask1_price", "ask1_size"]
        missing_cols = [col for col in key_cols if col not in df.columns]
        if missing_cols:
            print(f"\n警告: 缺少关键列: {missing_cols}")
        else:
            print(f"\n所有关键列已加载")
            print(f"\nOHLCV数据示例:")
            print(df.select(["timestamp", "open_price", "high_price", "low_price", "close_price"]).head(10))
            print(f"\n五档数据示例:")
            print(df.select(["timestamp", "bid1_price", "bid1_size", "ask1_price", "ask1_size"]).head(10))

        print(f"\n{'='*60}")
        print("数据质量验证")
        print(f"{'='*60}")
        validate_data(df)

    print(f"\n{'='*60}")
    print("测试日期范围数据加载")
    print(f"{'='*60}")
    range_df = load_and_merge_date_range("2023-01-03", "2023-01-06")
    if range_df is not None:
        print(f"\n日期范围数据预览:")
        print(range_df.head())
        print(f"形状: {range_df.shape}")
        print(f"\nOHLCV数据示例:")
        print(range_df.select(["timestamp", "date", "contract", "open_price", "high_price", "low_price", "close_price"]).head(10))
        validate_data(range_df)
