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
        DATA_ROOT,
        COMMODITY,
        SYMBOL,
        TIMEFRAME,
        ORDERBOOK_REQUIRED_COLUMNS,
    )
except ImportError:
    from config import (
        SHOW_PROGRESS,
        DATA_ROOT,
        COMMODITY,
        SYMBOL,
        TIMEFRAME,
        ORDERBOOK_REQUIRED_COLUMNS,
    )

# 配置日志
logger = logging.getLogger(__name__)


def get_orderbook_filepath(date_str: str, contract: str, commodity: str = COMMODITY, timeframe: str = TIMEFRAME) -> Path:
    """
    获取 orderbook 数据文件路径

    目录结构: data/品种/年份/orderbook/{timeframe}/合约-年-月-日_{timeframe}.csv

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD' (例: '2023-01-03')
        contract: 合约代码 (例: 'm2305')
        commodity: 品种名称 (默认: 从配置读取)
        timeframe: 时间粒度 (例: '30s' 或 '1m')

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

    dir_path = DATA_ROOT / commodity / year / "orderbook" / timeframe
    filename = f"{contract}-{date_str}_{timeframe}.csv"
    return dir_path / filename


def find_daily_contract(
    date_str: str,
    commodity: str = COMMODITY,
    timeframe: str = TIMEFRAME,
    symbol: str = SYMBOL,
) -> Optional[str]:
    """
    自动识别指定日期的合约代码（每天只有1份合约文件）

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        commodity: 品种名称
        timeframe: 时间粒度 (例: '30s' 或 '1m')
        symbol: 品种英文符号前缀 (例: 'al', 'fu')

    Returns:
        合约代码，未找到返回 None
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.strftime("%Y")
    except ValueError:
        return None

    dir_path = DATA_ROOT / commodity / year / "orderbook" / timeframe
    if not dir_path.exists():
        return None

    csv_files = list(dir_path.glob(f"*-{date_str}_{timeframe}.csv"))
    if symbol:
        symbol_lower = symbol.lower()
        csv_files = [f for f in csv_files if f.name.lower().startswith(symbol_lower)]
    if not csv_files:
        return None

    csv_files = sorted(csv_files, key=lambda p: p.name)
    if len(csv_files) > 1:
        logger.warning(f"{date_str} 发现多个合约文件，按文件名选择第一个: {csv_files[0].name}")

    # 从文件名提取合约代码：m2305-2023-01-03_30s.csv -> m2305
    return csv_files[0].stem.split('-')[0]


def load_daily_orderbook_data(
    date_str: str,
    contract: str = None,
    commodity: str = COMMODITY,
    timeframe: str = TIMEFRAME,
    symbol: str = SYMBOL,
) -> Optional[pl.DataFrame]:
    """
    加载单日 orderbook 数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        contract: 合约代码 (例: 'm2305')，如果为None则自动从目录识别
        commodity: 品种名称 (默认: 从配置读取)
        timeframe: 时间粒度 (例: '30s' 或 '1m')
        symbol: 品种英文符号前缀 (默认: 从配置读取)

    Returns:
        包含 orderbook 数据的 DataFrame
    """
    logger.info(
        f"加载日期 {date_str} 的 orderbook 数据 "
        f"(commodity={commodity}, symbol={symbol}, timeframe={timeframe})"
    )

    if contract is None:
        contract = find_daily_contract(
            date_str,
            commodity=commodity,
            timeframe=timeframe,
            symbol=symbol,
        )
        if contract is None:
            logger.error(
                f"日期 {date_str} 未找到合约文件 "
                f"(commodity={commodity}, symbol={symbol}, timeframe={timeframe})"
            )
            return None
        logger.info(f"自动识别合约: {contract}")

    filepath = get_orderbook_filepath(date_str, contract, commodity=commodity, timeframe=timeframe)
    if not filepath.exists():
        logger.warning(f"文件不存在: {filepath}")
        return None

    try:
        schema_df = pl.read_csv(filepath, n_rows=0)
        available_columns = [
            col for col in ORDERBOOK_REQUIRED_COLUMNS
            if col in schema_df.columns
        ]
        missing_columns = [
            col for col in ORDERBOOK_REQUIRED_COLUMNS
            if col not in schema_df.columns
        ]
        if not available_columns:
            logger.error(f"{filepath} 不包含任何可识别的 orderbook 列")
            return None
        if missing_columns:
            logger.warning(f"{filepath.name} 缺少部分基础列: {missing_columns}")

        df = pl.read_csv(filepath, columns=available_columns)
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
    commodity: str = COMMODITY,
    timeframe: str = TIMEFRAME,
    symbol: str = SYMBOL,
) -> Optional[pl.DataFrame]:
    """
    加载日期范围内的 orderbook 数据

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        contract: 合约代码，如果为None则每天自动识别
        commodity: 品种名称 (默认: 从配置读取)
        timeframe: 时间粒度 (例: '30s' 或 '1m')
        symbol: 品种英文符号前缀 (默认: 从配置读取)

    Returns:
        合并后的 DataFrame
    """
    date_list = generate_date_range(start_date, end_date)
    logger.info(
        f"准备加载 {len(date_list)} 天的数据，从 {start_date} 到 {end_date} "
        f"(commodity={commodity}, symbol={symbol}, timeframe={timeframe})"
    )

    if contract is not None:
        logger.info(f"使用固定合约: {contract}")

    # 存 (date_str, df) 以便后续打印问题文件
    all_dfs: list[tuple[str, pl.DataFrame]] = []
    for i, date_str in enumerate(date_list):
        if SHOW_PROGRESS and (i + 1) % 10 == 0:
            logger.info(f"进度: {i + 1}/{len(date_list)} 天")

        daily_df = load_daily_orderbook_data(
            date_str,
            contract,
            commodity=commodity,
            timeframe=timeframe,
            symbol=symbol,
        )
        if daily_df is not None:
            daily_df = daily_df.with_columns(pl.lit(date_str).alias("date"))
            all_dfs.append((date_str, daily_df))

    if not all_dfs:
        logger.warning("没有加载到任何数据")
        return None

    # 扫描所有文件的列类型，找出类型冲突的列
    col_types: dict[str, set] = {}
    for date_str, df in all_dfs:
        for col, dtype in df.schema.items():
            col_types.setdefault(col, set()).add(dtype)

    conflict_cols = {col: types for col, types in col_types.items() if len(types) > 1}
    if conflict_cols:
        logger.warning(f"发现 {len(conflict_cols)} 个列存在类型冲突，将统一转换为 Float64")
        for col, types in conflict_cols.items():
            logger.warning(f"  列 '{col}' 存在多种类型: {types}")
            for date_str, df in all_dfs:
                if col in df.schema:
                    logger.warning(f"    {date_str}: {df.schema[col]}")

        fixed_dfs = []
        for date_str, df in all_dfs:
            cols_to_cast = [
                col for col in conflict_cols
                if col in df.schema and df.schema[col] != pl.Float64
            ]
            if cols_to_cast:
                df = df.with_columns([pl.col(col).cast(pl.Float64) for col in cols_to_cast])
                logger.info(f"  {date_str} 已转换列: {cols_to_cast}")
            fixed_dfs.append(df)
        dfs_to_concat = fixed_dfs
    else:
        dfs_to_concat = [df for _, df in all_dfs]

    logger.info(f"合并 {len(dfs_to_concat)} 天的数据")
    merged_df = pl.concat(dfs_to_concat)
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
 
