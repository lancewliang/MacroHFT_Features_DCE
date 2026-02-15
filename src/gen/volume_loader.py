"""
成交量统计数据加载模块
负责从 DCE CSV 文件中读取成交量统计数据，并计算OHLCV K线数据
"""

import polars as pl
from pathlib import Path
from typing import List, Optional
import logging

try:
    # 尝试相对导入（当作为包导入时）
    from .config import (
        get_dce_filepath,
        DATA_TYPE_VOLUME,
        DCE_VOLUME_RENAME_MAP
    )
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from config import (
        get_dce_filepath,
        DATA_TYPE_VOLUME,
        DCE_VOLUME_RENAME_MAP
    )

# 配置日志
logger = logging.getLogger(__name__)


def load_daily_volume_data(date_str: str, contract_code: str) -> Optional[pl.DataFrame]:
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
    if not contract_code:
        logger.error("contract_code 参数不能为空")
        return None

    # 加载并合并所有合约的数据
 
    csv_path = get_dce_filepath(date_str, contract_code, DATA_TYPE_VOLUME)

    if not csv_path.exists():
        logger.warning(f"期货成交量统计数据文件不存在: {csv_path}")
        return None

    try:
        # 读取CSV文件
        df = pl.read_csv(csv_path)

        # 检查必要的列是否存在
        required_cols = ["TradingDay", "UpdateTime", "Price1"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"合约 {contract_code} 缺少必要列 {missing_cols}: {csv_path}")
            return None

        # 添加合约代码列
        df = df.with_columns(pl.lit(contract_code).alias("contract"))

 
        logger.debug(f"成功加载期货成交量统计数据: {date_str}, 合约: {contract_code}, 行数: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"读取期货成交量统计数据失败 {date_str}, 合约 {contract_code}: {str(e)}")
        return None



def calculate_ohlcv_from_volume_data(df: pl.DataFrame, window: str = "1m") -> pl.DataFrame:
    """
    从期货成交量统计数据计算K线OHLCV数据

    重要说明：期货成交量统计数据中的每一行都是快照（累计值），不是增量。

    根据文档1.4节，K线价格需要通过期货成交量统计数据计算：
    - open_price: 优先使用上一分钟的close_price，如果上一分钟不存在则使用窗口内第一行所有有效价格（Price1-5）的平均值
    - high_price: 窗口内所有 Price1-5 的最大值
    - low_price: 窗口内所有 Price1-5 的最小值
    - close_price: 窗口内最后一行所有有效价格（Price1-5）的平均值
    - volume: 窗口内成交量增量（最后值 - 第一值）
      因为数据是快照（累计值），所以计算增量而不是累加

    Args:
        df: 期货成交量统计原始数据（快照数据）
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

    # 1.5. 按合约和时间排序（从早到晚）
    df = df.sort(["contract", "timestamp"])

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
    # 注意：期货成交量统计数据中的每一行都是快照（累计值），所以需要计算增量
    ohlcv_df = df.group_by(["minute", "contract"]).agg([
        # Open: 临时使用窗口内第一行的所有有效价格的平均值（稍后会用上一分钟的close替换）
        pl.col("valid_prices").first().list.mean().alias("open_price_temp"),

        # High: 窗口内所有有效价格的最大值
        pl.col("valid_prices").flatten().max().alias("high_price"),

        # Low: 窗口内所有有效价格的最小值
        pl.col("valid_prices").flatten().min().alias("low_price"),

        # Close: 窗口内最后一行的所有有效价格的平均值
        pl.col("valid_prices").last().list.mean().alias("close_price"),

        # Volume: 窗口内成交量增量（最后值 - 第一值）
        # 因为数据是快照（累计值），所以要计算增量而不是累加
        (
            (pl.col("buy_open_vol1").last() - pl.col("buy_open_vol1").first()).fill_null(0) +
            (pl.col("buy_close_vol1").last() - pl.col("buy_close_vol1").first()).fill_null(0) +
            (pl.col("sell_open_vol1").last() - pl.col("sell_open_vol1").first()).fill_null(0) +
            (pl.col("sell_close_vol1").last() - pl.col("sell_close_vol1").first()).fill_null(0) +
            (pl.col("buy_open_vol2").last() - pl.col("buy_open_vol2").first()).fill_null(0) +
            (pl.col("buy_close_vol2").last() - pl.col("buy_close_vol2").first()).fill_null(0) +
            (pl.col("sell_open_vol2").last() - pl.col("sell_open_vol2").first()).fill_null(0) +
            (pl.col("sell_close_vol2").last() - pl.col("sell_close_vol2").first()).fill_null(0) +
            (pl.col("buy_open_vol3").last() - pl.col("buy_open_vol3").first()).fill_null(0) +
            (pl.col("buy_close_vol3").last() - pl.col("buy_close_vol3").first()).fill_null(0) +
            (pl.col("sell_open_vol3").last() - pl.col("sell_open_vol3").first()).fill_null(0) +
            (pl.col("sell_close_vol3").last() - pl.col("sell_close_vol3").first()).fill_null(0) +
            (pl.col("buy_open_vol4").last() - pl.col("buy_open_vol4").first()).fill_null(0) +
            (pl.col("buy_close_vol4").last() - pl.col("buy_close_vol4").first()).fill_null(0) +
            (pl.col("sell_open_vol4").last() - pl.col("sell_open_vol4").first()).fill_null(0) +
            (pl.col("sell_close_vol4").last() - pl.col("sell_close_vol4").first()).fill_null(0) +
            (pl.col("buy_open_vol5").last() - pl.col("buy_open_vol5").first()).fill_null(0) +
            (pl.col("buy_close_vol5").last() - pl.col("buy_close_vol5").first()).fill_null(0) +
            (pl.col("sell_open_vol5").last() - pl.col("sell_open_vol5").first()).fill_null(0) +
            (pl.col("sell_close_vol5").last() - pl.col("sell_close_vol5").first()).fill_null(0)
        ).alias("trade_volume2")
    ]).sort(["minute", "contract"])

    # 6. 使用上一分钟的 close_price 作为当前的 open_price
    # 优先使用上一分钟的 close_price，如果上一分钟不存在则使用第一行的平均价格
    ohlcv_df = ohlcv_df.with_columns([
        # 按合约分组，获取上一行的 timestamp
        pl.col("minute").shift(1).over("contract").alias("prev_minute"),
        # 按合约分组，获取上一行的 close_price
        pl.col("close_price").shift(1).over("contract").alias("prev_close_price")
    ])

    # 计算当前分钟 - 1分钟，用于判断上一行是否是真正的"上一分钟"
    ohlcv_df = ohlcv_df.with_columns([
        (pl.col("minute") - pl.duration(minutes=1)).alias("expected_prev_minute")
    ])

    # 更新 open_price：
    # 只有当上一行的时间等于当前时间-1分钟时，才使用上一行的 close_price
    # 否则认为上一分钟不存在，使用当前窗口第一行的平均价格
    ohlcv_df = ohlcv_df.with_columns([
        pl.when(pl.col("prev_minute") == pl.col("expected_prev_minute"))
        .then(pl.col("prev_close_price"))
        .otherwise(pl.col("open_price_temp"))
        .alias("open_price")
    ])

    # 删除临时列
    ohlcv_df = ohlcv_df.drop(["prev_minute", "prev_close_price", "expected_prev_minute", "open_price_temp"])

    # 重命名minute为timestamp
    ohlcv_df = ohlcv_df.rename({"minute": "timestamp"})

    logger.info(f"OHLCV计算完成，生成 {len(ohlcv_df)} 条K线数据")

    return ohlcv_df
