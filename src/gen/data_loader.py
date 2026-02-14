"""
数据加载模块
负责从 ZIP 文件中读取订单簿和K线数据，并进行预处理
"""

import polars as pl
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import logging

from config import (
    get_bookdepth_filepath,
    get_kline_filepath,
    SYMBOL,
    TIMEFRAME,
    LEVEL_NAMES,
    BID_LEVELS,
    ASK_LEVELS,
    KLINE_RENAME_MAP,
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


def load_daily_bookdepth(date_str: str) -> Optional[pl.DataFrame]:
    """
    从 ZIP 文件中读取单日订单簿数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'

    Returns:
        Polars DataFrame 或 None（如果文件不存在）

    DataFrame 格式:
        - timestamp: 时间戳
        - percentage: 档位 (-5 到 -1, 1 到 5)
        - depth: 订单深度
        - notional: 名义价值
    """
    zip_path = get_bookdepth_filepath(date_str)

    if not zip_path.exists():
        logger.warning(f"订单簿文件不存在: {zip_path}")
        return None

    try:
        # 从 ZIP 文件中读取 CSV
        with zipfile.ZipFile(zip_path, 'r') as z:
            # ZIP 文件中应该只有一个 CSV 文件
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                logger.error(f"ZIP 文件中没有 CSV 文件: {zip_path}")
                return None

            # 读取第一个 CSV 文件
            with z.open(csv_files[0]) as f:
                df = pl.read_csv(f)

        # 添加日期列用于调试
        df = df.with_columns(pl.lit(date_str).alias("date"))

        logger.debug(f"成功加载订单簿数据: {date_str}, 行数: {len(df)}")
        return df

    except Exception as e:
        logger.error(f"读取订单簿数据失败 {date_str}: {str(e)}")
        return None


def load_daily_kline(date_str: str) -> Optional[pl.DataFrame]:
    """
    从 ZIP 文件中读取单日K线数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'

    Returns:
        Polars DataFrame 或 None（如果文件不存在）

    DataFrame 格式:
        - open_time, open, high, low, close, volume, close_time,
          quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore
    """
    zip_path = get_kline_filepath(date_str)

    if not zip_path.exists():
        logger.warning(f"K线文件不存在: {zip_path}")
        return None

    try:
        # 从 ZIP 文件中读取 CSV
        with zipfile.ZipFile(zip_path, 'r') as z:
            # ZIP 文件中应该只有一个 CSV 文件
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                logger.error(f"ZIP 文件中没有 CSV 文件: {zip_path}")
                return None

            # 读取第一个 CSV 文件
            with z.open(csv_files[0]) as f:
                df = pl.read_csv(f)

        # 添加日期列用于调试
        df = df.with_columns(pl.lit(date_str).alias("date"))

        logger.debug(f"成功加载K线数据: {date_str}, 行数: {len(df)}")
        return df

    except Exception as e:
        logger.error(f"读取K线数据失败 {date_str}: {str(e)}")
        return None


def load_date_range_data(
    start_date: str,
    end_date: str,
    data_type: str = "both"
) -> Tuple[Optional[pl.DataFrame], Optional[pl.DataFrame]]:
    """
    加载日期范围内的所有数据

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        data_type: 数据类型 ("both", "bookdepth", "kline")

    Returns:
        (bookdepth_df, kline_df) 元组
    """
    date_list = generate_date_range(start_date, end_date)
    logger.info(f"准备加载 {len(date_list)} 天的数据，从 {start_date} 到 {end_date}")

    bookdepth_dfs = []
    kline_dfs = []

    for i, date_str in enumerate(date_list):
        if SHOW_PROGRESS and (i + 1) % 10 == 0:
            logger.info(f"进度: {i + 1}/{len(date_list)} 天")

        # 加载订单簿数据
        if data_type in ["both", "bookdepth"]:
            bd_df = load_daily_bookdepth(date_str)
            if bd_df is not None:
                bookdepth_dfs.append(bd_df)

        # 加载K线数据
        if data_type in ["both", "kline"]:
            kl_df = load_daily_kline(date_str)
            if kl_df is not None:
                kline_dfs.append(kl_df)

    # 合并所有日期的数据
    bookdepth_df = None
    kline_df = None

    if bookdepth_dfs:
        logger.info(f"合并 {len(bookdepth_dfs)} 天的订单簿数据")
        bookdepth_df = pl.concat(bookdepth_dfs)
        logger.info(f"订单簿总行数: {len(bookdepth_df)}")

    if kline_dfs:
        logger.info(f"合并 {len(kline_dfs)} 天的K线数据")
        kline_df = pl.concat(kline_dfs)
        logger.info(f"K线总行数: {len(kline_df)}")

    return bookdepth_df, kline_df


def pivot_bookdepth(df: pl.DataFrame) -> pl.DataFrame:
    """
    将订单簿长格式转换为宽格式

    输入格式:
        timestamp, percentage, depth, notional

    输出格式:
        timestamp, bid1_price, bid1_size, bid2_price, bid2_size, ...,
        ask1_price, ask1_size, ask2_price, ask2_size, ...

    Args:
        df: 长格式订单簿数据

    Returns:
        宽格式订单簿数据
    """
    logger.info("开始转换订单簿格式（长格式 -> 宽格式）")

    # 转换 timestamp 为 datetime 类型（如果是字符串）
    if df["timestamp"].dtype == pl.Utf8:
        df = df.with_columns(
            pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S")
        )

    # 先计算价格：price = notional / depth
    df = df.with_columns(
        (pl.col("notional") / pl.col("depth")).alias("price")
    )

    # 创建结果列表
    pivoted_dfs = []

    # 为每个档位创建单独的列
    for level in BID_LEVELS + ASK_LEVELS:
        level_name = LEVEL_NAMES[level]

        # 筛选当前档位的数据
        level_df = df.filter(pl.col("percentage") == level).select([
            "timestamp",
            pl.col("price").alias(f"{level_name}_price"),
            pl.col("depth").alias(f"{level_name}_size")
        ])

        pivoted_dfs.append(level_df)

    # 按时间戳合并所有档位
    # 使用 inner join 并且只保留一个 timestamp 列
    result = pivoted_dfs[0]
    for i, level_df in enumerate(pivoted_dfs[1:], 1):
        # 删除 level_df 中的 timestamp 列，使用索引对齐
        # 先按 timestamp 排序确保顺序一致
        result = result.sort("timestamp")
        level_df = level_df.sort("timestamp")

        # 使用 hstack 水平拼接（假设timestamp已对齐）
        # 但为了安全，还是使用 join
        result = result.join(level_df, on="timestamp", how="inner", suffix=f"_{i}")

        # 删除可能产生的重复 timestamp 列
        timestamp_cols = [col for col in result.columns if col.startswith("timestamp_")]
        if timestamp_cols:
            result = result.drop(timestamp_cols)

    # 按时间戳排序
    result = result.sort("timestamp")

    # 只保留每分钟最接近准点的数据
    # 策略：对每分钟分组，选择秒数最小的那一条
    original_rows = len(result)

    # 添加辅助列：分钟级别的时间戳（去掉秒数）
    result = result.with_columns([
        pl.col("timestamp").dt.truncate("1m").alias("minute"),
        pl.col("timestamp").dt.second().alias("second")
    ])

    # 对每分钟分组，选择秒数最小的那一条
    result = (
        result
        .sort(["minute", "second"])  # 按分钟和秒数排序
        .group_by("minute")
        .first()  # 每组取第一条（秒数最小）
        .drop(["minute", "second"])  # 删除辅助列
        .sort("timestamp")
    )

    filtered_rows = len(result)

    logger.info(f"订单簿格式转换完成，行数: {original_rows} -> {filtered_rows} (每分钟保留1条)")
    if original_rows > filtered_rows:
        logger.info(f"过滤掉同分钟的重复数据: {original_rows - filtered_rows} 行")

    return result


def preprocess_kline(df: pl.DataFrame) -> pl.DataFrame:
    """
    预处理K线数据

    处理步骤:
    1. 转换时间戳（毫秒 -> 日期时间）
    2. 重命名列（open -> open_price, etc.）
    3. 选择需要的列

    Args:
        df: 原始K线数据

    Returns:
        预处理后的K线数据
    """
    logger.info("开始预处理K线数据")

    # 转换时间戳（Unix毫秒 -> 日期时间）
    df = df.with_columns(
        pl.from_epoch(pl.col("open_time"), time_unit="ms").alias("timestamp")
    )

    # 重命名列
    df = df.rename(KLINE_RENAME_MAP)

    # 保留 close 列（作为 close_price 的副本）
    df = df.with_columns(
        pl.col("close_price").alias("close")
    )

    # 选择需要的列
    columns_to_keep = [
        "timestamp",
        "open_price", "high_price", "low_price", "close_price", "close",
        "traded_volume", "taker_buy_volume", "count"
    ]

    df = df.select(columns_to_keep)

    logger.info(f"K线数据预处理完成，行数: {len(df)}")
    return df


def merge_data(bookdepth_df: pl.DataFrame, kline_df: pl.DataFrame) -> pl.DataFrame:
    """
    按时间戳合并订单簿和K线数据

    Args:
        bookdepth_df: 宽格式订单簿数据
        kline_df: 预处理后的K线数据

    Returns:
        合并后的数据

    输出格式:
        timestamp, open_price, high_price, low_price, close_price,
        bid1_price, bid1_size, ..., ask5_price, ask5_size,
        volume, taker_buy_volume, count
    """
    logger.info("开始合并订单簿和K线数据")

    # 确保时间戳格式一致
    # bookdepth 的 timestamp 可能是字符串，需要转换
    if bookdepth_df["timestamp"].dtype == pl.Utf8:
        # 尝试多种时间格式
        try:
            # 格式1: "2023-06-30 15:07:31" (带秒)
            bookdepth_df = bookdepth_df.with_columns(
                pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S")
            )
        except:
            try:
                # 格式2: "2023/06/30 15:07" (不带秒，斜杠分隔)
                bookdepth_df = bookdepth_df.with_columns(
                    pl.col("timestamp").str.strptime(pl.Datetime, "%Y/%m/%d %H:%M")
                )
            except:
                # 格式3: "2023-06-30 15:07" (不带秒，短横线分隔)
                bookdepth_df = bookdepth_df.with_columns(
                    pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M")
                )

    # 统一时间戳精度为毫秒（ms）并截断到分钟
    # K线数据是分钟级别，订单簿可能带秒
    # 将时间戳截断到分钟级别以提高匹配率
    kline_df = kline_df.with_columns(
        pl.col("timestamp").cast(pl.Datetime("ms")).dt.truncate("1m").alias("timestamp")
    )
    bookdepth_df = bookdepth_df.with_columns(
        pl.col("timestamp").cast(pl.Datetime("ms")).dt.truncate("1m").alias("timestamp")
    )

    # 内连接（只保留两个数据集都有的时间戳）
    merged = kline_df.join(bookdepth_df, on="timestamp", how="inner")

    logger.info(f"数据合并完成，行数: {len(merged)}")

    # 检查合并后的数据完整性
    if len(merged) > 0:
        null_counts = merged.null_count()
        # Polars 的 sum() 返回的是 DataFrame，需要取所有列的和
        total_nulls = null_counts.sum().to_dicts()[0]
        total_nulls_sum = sum(total_nulls.values())

        if total_nulls_sum > 0:
            logger.warning(f"合并后存在 {total_nulls_sum} 个空值")
            logger.debug(f"空值统计:\n{null_counts}")

    return merged


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
            passed = False
    else:
        logger.warning("数据为空，跳过验证")
        return False

    # 检查 bid1_price < ask1_price
    invalid_spread = df.filter(pl.col("bid1_price") >= pl.col("ask1_price"))
    if len(invalid_spread) > 0:
        logger.error(f"发现 {len(invalid_spread)} 行数据的 bid1_price >= ask1_price")
        passed = False

    # 检查负值
    price_columns = [col for col in df.columns if "price" in col]
    for col in price_columns:
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
    test_date = "2023-06-30"
    print(f"\n{'='*60}")
    print(f"测试加载单日数据: {test_date}")
    print(f"{'='*60}")

    # 加载订单簿数据
    bd_df = load_daily_bookdepth(test_date)
    if bd_df is not None:
        print(f"\n订单簿数据预览:")
        print(bd_df.head())
        print(f"形状: {bd_df.shape}")

    # 加载K线数据
    kl_df = load_daily_kline(test_date)
    if kl_df is not None:
        print(f"\nK线数据预览:")
        print(kl_df.head())
        print(f"形状: {kl_df.shape}")

    # 测试订单簿格式转换
    if bd_df is not None:
        print(f"\n{'='*60}")
        print("测试订单簿格式转换")
        print(f"{'='*60}")
        pivoted = pivot_bookdepth(bd_df)
        print(f"\n宽格式订单簿预览:")
        print(pivoted.head())
        print(f"列名: {pivoted.columns}")

    # 测试K线预处理
    if kl_df is not None:
        print(f"\n{'='*60}")
        print("测试K线预处理")
        print(f"{'='*60}")
        processed_kl = preprocess_kline(kl_df)
        print(f"\n预处理后K线预览:")
        print(processed_kl.head())
        print(f"列名: {processed_kl.columns}")

    # 测试数据合并
    if bd_df is not None and kl_df is not None:
        print(f"\n{'='*60}")
        print("测试数据合并")
        print(f"{'='*60}")
        pivoted = pivot_bookdepth(bd_df)
        processed_kl = preprocess_kline(kl_df)
        merged = merge_data(pivoted, processed_kl)
        print(f"\n合并后数据预览:")
        print(merged.head())
        print(f"形状: {merged.shape}")
        print(f"列名: {merged.columns}")

        # 验证数据
        validate_data(merged)
