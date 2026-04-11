"""
因子计算模块
实现所有因子的计算逻辑
"""

import polars as pl
import numpy as np
import logging
from typing import List

logger = logging.getLogger(__name__)

ROLLING_WINDOWS = [60, 180, 360]
RELATIVE_WINDOWS = [20, 60, 180, 360]


def _group_keys(df: pl.DataFrame) -> list[str]:
    """返回适合做快照差分的分组键。"""
    return [key for key in ("date", "contract") if key in df.columns]


def _shift_within_groups(expr: pl.Expr, periods: int, group_keys: list[str]) -> pl.Expr:
    """在日内分组内做 shift，避免累计快照跨日串联。"""
    if group_keys:
        return expr.shift(periods).over(group_keys)
    return expr.shift(periods)


def _endpoint_slope_expr(column: str, window: int, group_keys: list[str]) -> pl.Expr:
    """用窗口首尾差近似每步斜率。"""
    prev_value = _shift_within_groups(pl.col(column), window, group_keys)
    return ((pl.col(column) - prev_value) / float(window)).alias(f"{column}_slope_{window}")


def _rolling_zscore_expr(column: str, window: int, alias: str) -> pl.Expr:
    """构造滚动 z-score 表达式。"""
    rolling_mean = pl.col(column).rolling_mean(window_size=window)
    rolling_std = pl.col(column).rolling_std(window_size=window)
    return ((pl.col(column) - rolling_mean) / (rolling_std + 1e-8)).alias(alias)


def _rolling_ratio_expr(column: str, window: int, alias: str) -> pl.Expr:
    """构造当前值相对滚动均值的比值表达式。"""
    rolling_mean = pl.col(column).rolling_mean(window_size=window)
    return (pl.col(column) / (rolling_mean + 1e-8)).alias(alias)


def _tick_proxy_expr() -> pl.Expr:
    """用盘口相邻价差的最小正值近似 tick。"""
    return pl.min_horizontal(
        pl.when((pl.col("bid1_price") - pl.col("bid2_price")) > 0).then(pl.col("bid1_price") - pl.col("bid2_price")),
        pl.when((pl.col("bid2_price") - pl.col("bid3_price")) > 0).then(pl.col("bid2_price") - pl.col("bid3_price")),
        pl.when((pl.col("bid3_price") - pl.col("bid4_price")) > 0).then(pl.col("bid3_price") - pl.col("bid4_price")),
        pl.when((pl.col("bid4_price") - pl.col("bid5_price")) > 0).then(pl.col("bid4_price") - pl.col("bid5_price")),
        pl.when((pl.col("ask2_price") - pl.col("ask1_price")) > 0).then(pl.col("ask2_price") - pl.col("ask1_price")),
        pl.when((pl.col("ask3_price") - pl.col("ask2_price")) > 0).then(pl.col("ask3_price") - pl.col("ask2_price")),
        pl.when((pl.col("ask4_price") - pl.col("ask3_price")) > 0).then(pl.col("ask4_price") - pl.col("ask3_price")),
        pl.when((pl.col("ask5_price") - pl.col("ask4_price")) > 0).then(pl.col("ask5_price") - pl.col("ask4_price")),
        pl.when((pl.col("ask1_price") - pl.col("bid1_price")) > 0).then(pl.col("ask1_price") - pl.col("bid1_price")),
    ).fill_null(0.0).alias("_tick_proxy")


# ==================== K线特征因子 ====================
def calculate_kline_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算K线相关的特征因子

    因子列表:
    - kmid: K线实体中点 (close - open)
    - kmid2: K线实体比率 ((close - open) / (high - low))
    - klen: K线长度 (high - low)
    - kup: 上影线长度 (high - max(open, close))
    - kup2: 上影线比率 (kup / klen)
    - klow: 下影线长度 (min(open, close) - low)
    - klow2: 下影线比率 (klow / klen)
    - ksft: K线偏移 (2*close - high - low)
    - ksft2: K线偏移比率 (ksft / klen)

    Args:
        df: 包含 open_price, high_price, low_price, close_price 的数据框

    Returns:
        添加了K线特征因子的数据框
    """
    logger.info("开始计算K线特征因子")

    # 基础变量
    max_oc = pl.max_horizontal("open_price", "close_price").alias("max_oc")
    min_oc = pl.min_horizontal("open_price", "close_price").alias("min_oc")

    # K线长度（用于除法，需要避免除零）
    klen = (pl.col("high_price") - pl.col("low_price")).alias("klen")

    # 计算所有K线特征
    df = df.with_columns([
        # 实体中点
        (pl.col("close_price") - pl.col("open_price")).alias("kmid"),

        # K线长度
        klen,

        # 辅助列
        max_oc,
        min_oc
    ])

    # 计算依赖于 klen 的比率特征（需要处理除零）
    df = df.with_columns([
        # 实体比率
        pl.when(pl.col("klen") != 0)
          .then((pl.col("close_price") - pl.col("open_price")) / pl.col("klen"))
          .otherwise(0)
          .alias("kmid2"),

        # 上影线
        (pl.col("high_price") - pl.col("max_oc")).alias("kup"),

        # 下影线
        (pl.col("min_oc") - pl.col("low_price")).alias("klow"),

        # K线偏移
        (2 * pl.col("close_price") - pl.col("high_price") - pl.col("low_price")).alias("ksft")
    ])

    # 计算比率特征
    df = df.with_columns([
        # 上影线比率
        pl.when(pl.col("klen") != 0)
          .then(pl.col("kup") / pl.col("klen"))
          .otherwise(0)
          .alias("kup2"),

        # 下影线比率
        pl.when(pl.col("klen") != 0)
          .then(pl.col("klow") / pl.col("klen"))
          .otherwise(0)
          .alias("klow2"),

        # K线偏移比率
        pl.when(pl.col("klen") != 0)
          .then(pl.col("ksft") / pl.col("klen"))
          .otherwise(0)
          .alias("ksft2")
    ])

    # 删除辅助列
    df = df.drop(["max_oc", "min_oc"])

    logger.info("K线特征因子计算完成")
    return df


# ==================== 订单簿基础因子 ====================
def calculate_volume_and_normalized_size(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算总订单量和归一化订单量

    因子:
    - volume: 总订单量（所有档位之和）
    - bid1_size_n ~ bid5_size_n: 买方归一化订单量
    - ask1_size_n ~ ask5_size_n: 卖方归一化订单量

    Args:
        df: 包含 bid/ask size 的数据框

    Returns:
        添加了归一化订单量的数据框
    """
    logger.info("开始计算归一化订单量")

    # 计算总订单量
    volume_expr = pl.lit(0)
    for i in range(1, 6):
        volume_expr = volume_expr + pl.col(f"bid{i}_size") + pl.col(f"ask{i}_size")

    df = df.with_columns(volume_expr.alias("volume"))

    # 计算归一化订单量
    normalized_cols = []
    for i in range(1, 6):
        normalized_cols.extend([
            (pl.col(f"bid{i}_size") / pl.col("volume")).alias(f"bid{i}_size_n"),
            (pl.col(f"ask{i}_size") / pl.col("volume")).alias(f"ask{i}_size_n")
        ])

    df = df.with_columns(normalized_cols)

    logger.info("归一化订单量计算完成")
    return df


def calculate_wap_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算加权平均价格（WAP）因子

    因子:
    - wap_1: 第一档WAP = (ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)
    - wap_2: 第二档WAP = (ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)
    - wap_balance: abs(wap_1 - wap_2)

    Args:
        df: 包含 bid/ask price 和 size 的数据框

    Returns:
        添加了WAP因子的数据框
    """
    logger.info("开始计算WAP因子")

    df = df.with_columns([
        # wap_1
        ((pl.col("ask1_size") * pl.col("bid1_price") + pl.col("bid1_size") * pl.col("ask1_price"))
         / (pl.col("ask1_size") + pl.col("bid1_size"))).alias("wap_1"),

        # wap_2
        ((pl.col("ask2_size") * pl.col("bid2_price") + pl.col("bid2_size") * pl.col("ask2_price"))
         / (pl.col("ask2_size") + pl.col("bid2_size"))).alias("wap_2")
    ])

    # wap_balance
    df = df.with_columns(
        (pl.col("wap_1") - pl.col("wap_2")).abs().alias("wap_balance")
    )

    logger.info("WAP因子计算完成")
    return df


def calculate_trade_snapshot_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算基于成交量/成交额/持仓量快照的衍生因子。

    说明：
    - total_trade_volume / turnover / open_interest 都是快照字段
    - 成交类因子先做相邻快照差分，再参与后续计算

    因子:
    - trade_volume_delta
    - turnover_delta
    - avg_trade_price
    - avg_trade_price_bias
    - avg_trade_price_mid_bias
    - avg_trade_price_bias_change
    - open_interest_change
    - open_interest_change_ratio
    - open_interest_change_per_trade
    - open_interest_price_link
    """
    logger.info("开始计算成交与持仓快照衍生因子")

    group_keys = _group_keys(df)
    prev_trade_volume = _shift_within_groups(pl.col("total_trade_volume"), 1, group_keys)
    prev_turnover = _shift_within_groups(pl.col("turnover"), 1, group_keys)
    prev_open_interest = _shift_within_groups(pl.col("open_interest"), 1, group_keys)

    trade_volume_delta_raw = pl.col("total_trade_volume") - prev_trade_volume
    turnover_delta_raw = pl.col("turnover") - prev_turnover
    open_interest_change = (
        pl.when(prev_open_interest.is_not_null())
        .then(pl.col("open_interest") - prev_open_interest)
        .otherwise(0.0)
    )

    df = df.with_columns([
        pl.when(prev_trade_volume.is_not_null() & (trade_volume_delta_raw >= 0))
        .then(trade_volume_delta_raw)
        .otherwise(0.0)
        .alias("trade_volume_delta"),
        pl.when(prev_turnover.is_not_null() & (turnover_delta_raw >= 0))
        .then(turnover_delta_raw)
        .otherwise(0.0)
        .alias("turnover_delta"),
        open_interest_change.alias("open_interest_change"),
    ])

    df = df.with_columns([
        ((pl.col("ask1_price") + pl.col("bid1_price")) / 2.0).alias("_mid_price"),
        pl.when(pl.col("trade_volume_delta") > 0)
        .then(pl.col("turnover_delta") / (pl.col("trade_volume_delta") + 1e-8))
        .otherwise(pl.col("close_price"))
        .alias("avg_trade_price"),
        (pl.col("open_interest_change") / (prev_open_interest.abs() + 1e-8))
        .fill_null(0.0)
        .alias("open_interest_change_ratio"),
        (pl.col("open_interest_change") / (pl.col("trade_volume_delta") + 1e-8))
        .fill_null(0.0)
        .alias("open_interest_change_per_trade"),
    ])

    df = df.with_columns([
        ((pl.col("avg_trade_price") - pl.col("wap_1")) / (pl.col("wap_1") + 1e-8)).alias("avg_trade_price_bias"),
        ((pl.col("avg_trade_price") - pl.col("_mid_price")) / (pl.col("_mid_price") + 1e-8)).alias("avg_trade_price_mid_bias"),
    ])

    df = df.with_columns(
        (pl.col("avg_trade_price_bias") - _shift_within_groups(pl.col("avg_trade_price_bias"), 1, group_keys))
        .fill_null(0.0)
        .alias("avg_trade_price_bias_change")
    )

    df = df.drop("_mid_price")

    logger.info("成交与持仓快照衍生因子计算完成")
    return df


def calculate_spread_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算价差因子

    因子:
    - buy_spread: abs(bid1_price - bid5_price)
    - sell_spread: abs(ask1_price - ask5_price)
    - price_spread: 2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)

    Args:
        df: 包含 bid/ask price 的数据框

    Returns:
        添加了价差因子的数据框
    """
    logger.info("开始计算价差因子")

    df = df.with_columns([
        # 买方价差
        (pl.col("bid1_price") - pl.col("bid5_price")).abs().alias("buy_spread"),

        # 卖方价差
        (pl.col("ask1_price") - pl.col("ask5_price")).abs().alias("sell_spread"),

        # 买卖价差（归一化）
        (2 * (pl.col("ask1_price") - pl.col("bid1_price"))
         / (pl.col("ask1_price") + pl.col("bid1_price"))).alias("price_spread")
    ])

    logger.info("价差因子计算完成")
    return df


def calculate_gap_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算缺档因子。

    因子:
    - bid_gap_i_j = (bid_i - bid_j) / tick - 1
    - ask_gap_i_j = (ask_j - ask_i) / tick - 1
    """
    logger.info("开始计算缺档因子")

    df = df.with_columns(_tick_proxy_expr())

    exprs = []
    for i in range(1, 5):
        bid_gap = pl.col(f"bid{i}_price") - pl.col(f"bid{i+1}_price")
        ask_gap = pl.col(f"ask{i+1}_price") - pl.col(f"ask{i}_price")
        exprs.extend([
            pl.when(pl.col("_tick_proxy") > 0)
            .then(bid_gap / (pl.col("_tick_proxy") + 1e-8) - 1.0)
            .otherwise(0.0)
            .alias(f"bid_gap_{i}_{i+1}"),
            pl.when(pl.col("_tick_proxy") > 0)
            .then(ask_gap / (pl.col("_tick_proxy") + 1e-8) - 1.0)
            .otherwise(0.0)
            .alias(f"ask_gap_{i}_{i+1}"),
        ])

    df = df.with_columns(exprs)
    bid_gap_near_sum = pl.col("bid_gap_1_2") + pl.col("bid_gap_2_3")
    bid_gap_far_sum = pl.col("bid_gap_3_4") + pl.col("bid_gap_4_5")
    ask_gap_near_sum = pl.col("ask_gap_1_2") + pl.col("ask_gap_2_3")
    ask_gap_far_sum = pl.col("ask_gap_3_4") + pl.col("ask_gap_4_5")
    df = df.with_columns([
        (
            (pl.col("bid_gap_1_2") > 0).cast(pl.Int64)
            + (pl.col("bid_gap_2_3") > 0).cast(pl.Int64)
            + (pl.col("bid_gap_3_4") > 0).cast(pl.Int64)
            + (pl.col("bid_gap_4_5") > 0).cast(pl.Int64)
        ).alias("bid_gap_count"),
        pl.max_horizontal("bid_gap_1_2", "bid_gap_2_3", "bid_gap_3_4", "bid_gap_4_5").alias("max_bid_gap"),
        ((bid_gap_near_sum - bid_gap_far_sum) / (bid_gap_near_sum.abs() + bid_gap_far_sum.abs() + 1e-8))
        .alias("bid_gap_near_far_ratio"),
        (
            (pl.col("ask_gap_1_2") > 0).cast(pl.Int64)
            + (pl.col("ask_gap_2_3") > 0).cast(pl.Int64)
            + (pl.col("ask_gap_3_4") > 0).cast(pl.Int64)
            + (pl.col("ask_gap_4_5") > 0).cast(pl.Int64)
        ).alias("ask_gap_count"),
        pl.max_horizontal("ask_gap_1_2", "ask_gap_2_3", "ask_gap_3_4", "ask_gap_4_5").alias("max_ask_gap"),
        ((ask_gap_near_sum - ask_gap_far_sum) / (ask_gap_near_sum.abs() + ask_gap_far_sum.abs() + 1e-8))
        .alias("ask_gap_near_far_ratio"),
    ])
    df = df.with_columns([
        (pl.col("bid_gap_count") - pl.col("ask_gap_count")).alias("gap_count_diff"),
        (pl.col("max_bid_gap") - pl.col("max_ask_gap")).alias("max_gap_diff"),
        (pl.col("bid_gap_near_far_ratio") - pl.col("ask_gap_near_far_ratio")).alias("gap_near_far_ratio_diff"),
    ])
    df = df.drop("_tick_proxy")

    logger.info("缺档因子计算完成")
    return df


def calculate_volume_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算成交量因子

    因子:
    - buy_volume: bid1_size + ... + bid5_size
    - sell_volume: ask1_size + ... + ask5_size
    - volume_imbalance: (buy_volume - sell_volume) / (buy_volume + sell_volume)

    Args:
        df: 包含 bid/ask size 的数据框

    Returns:
        添加了成交量因子的数据框
    """
    logger.info("开始计算成交量因子")

    # 买方总量
    buy_volume_expr = pl.lit(0)
    for i in range(1, 6):
        buy_volume_expr = buy_volume_expr + pl.col(f"bid{i}_size")

    # 卖方总量
    sell_volume_expr = pl.lit(0)
    for i in range(1, 6):
        sell_volume_expr = sell_volume_expr + pl.col(f"ask{i}_size")

    df = df.with_columns([
        buy_volume_expr.alias("buy_volume"),
        sell_volume_expr.alias("sell_volume")
    ])

    # 成交量不平衡度
    df = df.with_columns(
        ((pl.col("buy_volume") - pl.col("sell_volume"))
         / (pl.col("buy_volume") + pl.col("sell_volume"))).alias("volume_imbalance")
    )

    logger.info("成交量因子计算完成")
    return df


def calculate_depth_balance_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算分层不平衡、加权深度不平衡与队列集中度因子

    因子:
    - imbalance_top1 / imbalance_top3 / imbalance_top5
    - weighted_imbalance_inv
    - bid1_queue_concentration / ask1_queue_concentration
    - top2_depth_share

    Args:
        df: 包含 bid/ask size 以及 buy_volume/sell_volume 的数据框

    Returns:
        添加了深度平衡与队列集中度因子的数据框
    """
    logger.info("开始计算分层不平衡与队列集中度因子")

    buy_top3 = pl.col("bid1_size") + pl.col("bid2_size") + pl.col("bid3_size")
    sell_top3 = pl.col("ask1_size") + pl.col("ask2_size") + pl.col("ask3_size")
    total_top2_depth = pl.col("bid1_size") + pl.col("bid2_size") + pl.col("ask1_size") + pl.col("ask2_size")

    weighted_buy = sum((pl.col(f"bid{i}_size") / float(i) for i in range(1, 6)), pl.lit(0.0))
    weighted_sell = sum((pl.col(f"ask{i}_size") / float(i) for i in range(1, 6)), pl.lit(0.0))

    df = df.with_columns([
        ((pl.col("bid1_size") - pl.col("ask1_size")) / (pl.col("bid1_size") + pl.col("ask1_size") + 1e-8))
        .alias("imbalance_top1"),
        ((buy_top3 - sell_top3) / (buy_top3 + sell_top3 + 1e-8)).alias("imbalance_top3"),
        ((pl.col("buy_volume") - pl.col("sell_volume")) / (pl.col("buy_volume") + pl.col("sell_volume") + 1e-8))
        .alias("imbalance_top5"),
        ((weighted_buy - weighted_sell) / (weighted_buy + weighted_sell + 1e-8)).alias("weighted_imbalance_inv"),
        (pl.col("bid1_size") / (pl.col("buy_volume") + 1e-8)).alias("bid1_queue_concentration"),
        (pl.col("ask1_size") / (pl.col("sell_volume") + 1e-8)).alias("ask1_queue_concentration"),
        (total_top2_depth / (pl.col("buy_volume") + pl.col("sell_volume") + 1e-8)).alias("top2_depth_share"),
    ])

    logger.info("分层不平衡与队列集中度因子计算完成")
    return df


def calculate_vwap_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算成交量加权平均价格（VWAP）因子

    因子:
    - sell_vwap: ask1_size_n * ask1_price + ... + ask5_size_n * ask5_price
    - buy_vwap: bid1_size_n * bid1_price + ... + bid5_size_n * bid5_price

    Args:
        df: 包含 bid/ask price, size_n 的数据框

    Returns:
        添加了VWAP因子的数据框
    """
    logger.info("开始计算VWAP因子")

    # 卖方VWAP
    sell_vwap_expr = pl.lit(0)
    for i in range(1, 6):
        sell_vwap_expr = sell_vwap_expr + (pl.col(f"ask{i}_size_n") * pl.col(f"ask{i}_price"))

    # 买方VWAP
    buy_vwap_expr = pl.lit(0)
    for i in range(1, 6):
        buy_vwap_expr = buy_vwap_expr + (pl.col(f"bid{i}_size_n") * pl.col(f"bid{i}_price"))

    df = df.with_columns([
        sell_vwap_expr.alias("sell_vwap"),
        buy_vwap_expr.alias("buy_vwap")
    ])

    logger.info("VWAP因子计算完成")
    return df


# ==================== 对数收益率因子 ====================
def calculate_log_return_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算对数收益率因子

    因子:
    - log_return_bid1_price: log(bid1_price[t] / bid1_price[t-1])
    - log_return_bid2_price: log(bid2_price[t] / bid2_price[t-1])
    - log_return_ask1_price: log(ask1_price[t] / ask1_price[t-1])
    - log_return_ask2_price: log(ask2_price[t] / ask2_price[t-1])
    - log_return_wap_1: log(wap_1[t] / wap_1[t-1])
    - log_return_wap_2: log(wap_2[t] / wap_2[t-1])

    注意：第一行数据会有 null 值（没有 t-1 数据）

    Args:
        df: 包含价格数据的数据框

    Returns:
        添加了对数收益率因子的数据框
    """
    logger.info("开始计算对数收益率因子")

    # 需要计算对数收益率的列
    price_columns = [
        "bid1_price", "bid2_price",
        "ask1_price", "ask2_price",
        "wap_1", "wap_2"
    ]

    log_return_exprs = []
    for col in price_columns:
        # 获取前一行的值
        prev_col = pl.col(col).shift(1)

        # 计算对数收益率: log(price[t] / price[t-1])
        log_return = (pl.col(col) / prev_col).log().alias(f"log_return_{col}")
        log_return_exprs.append(log_return)

    df = df.with_columns(log_return_exprs)

    logger.info("对数收益率因子计算完成")
    logger.warning("注意：第一行的对数收益率因子为 null（无前值数据）")

    return df


def calculate_stability_features(df: pl.DataFrame, windows: list[int] = ROLLING_WINDOWS) -> pl.DataFrame:
    """
    计算稳定性因子

    因子:
    - best_spread_duration: 最优价差连续不变的快照数
    - best_quote_duration: 买一卖一报价对连续不变的快照数
    - log_return_wap_1_vol_{window}: log_return_wap_1 的多窗口滚动波动率

    Args:
        df: 包含 price_spread, bid1_price, ask1_price, log_return_wap_1 的数据框
        windows: 滚动窗口列表，默认 [60, 180, 360]

    Returns:
        添加了稳定性因子的数据框
    """
    logger.info(f"开始计算稳定性因子 (windows={windows})")

    spread_change = (
        pl.col("price_spread").ne(pl.col("price_spread").shift(1)).fill_null(True)
    )
    quote_change = (
        (
            pl.col("bid1_price").ne(pl.col("bid1_price").shift(1))
            | pl.col("ask1_price").ne(pl.col("ask1_price").shift(1))
        )
        .fill_null(True)
    )

    df = df.with_columns([
        spread_change.cast(pl.Int64).cum_sum().alias("_spread_run_id"),
        quote_change.cast(pl.Int64).cum_sum().alias("_quote_run_id"),
    ])

    stability_exprs = [
        pl.col("_spread_run_id").cum_count().over("_spread_run_id").alias("best_spread_duration"),
        pl.col("_quote_run_id").cum_count().over("_quote_run_id").alias("best_quote_duration"),
    ]
    for window in windows:
        stability_exprs.append(
            pl.col("log_return_wap_1").rolling_std(window_size=window).alias(f"log_return_wap_1_vol_{window}")
        )

    df = df.with_columns(stability_exprs)

    df = df.drop(["_spread_run_id", "_quote_run_id"])

    logger.info("稳定性因子计算完成")
    logger.warning(f"注意：前 {max(windows)} 行的滚动波动率因子可能为 null（滚动窗口不足）")
    return df


def calculate_order_flow_features(df: pl.DataFrame, windows: list[int] = ROLLING_WINDOWS) -> pl.DataFrame:
    """
    计算订单流失衡因子

    因子:
    - ofi: 基于相邻快照 bid1/ask1 价格与数量变化构造的一阶 Order Flow Imbalance
    - ofi_{window}: ofi 的多窗口滚动累积值

    Args:
        df: 包含 bid1/ask1 价格和数量的数据框
        windows: 滚动窗口列表，默认 [60, 180, 360]

    Returns:
        添加了订单流失衡因子的数据框
    """
    logger.info(f"开始计算订单流失衡因子 (windows={windows})")

    bid_flow = (
        pl.when(pl.col("bid1_price") >= pl.col("bid1_price").shift(1))
        .then(pl.col("bid1_size"))
        .otherwise(0)
        - pl.when(pl.col("bid1_price") <= pl.col("bid1_price").shift(1))
        .then(pl.col("bid1_size").shift(1))
        .otherwise(0)
    )
    ask_flow = (
        pl.when(pl.col("ask1_price") <= pl.col("ask1_price").shift(1))
        .then(pl.col("ask1_size"))
        .otherwise(0)
        - pl.when(pl.col("ask1_price") >= pl.col("ask1_price").shift(1))
        .then(pl.col("ask1_size").shift(1))
        .otherwise(0)
    )

    df = df.with_columns((bid_flow - ask_flow).alias("ofi"))
    df = df.with_columns([
        pl.col("ofi").rolling_sum(window_size=window).alias(f"ofi_{window}")
        for window in windows
    ])

    logger.info("订单流失衡因子计算完成")
    logger.warning(f"注意：前 {max(windows)} 行的滚动 OFI 因子可能为 null（滚动窗口不足）")
    return df


def calculate_volatility_features(df: pl.DataFrame, windows: list[int] = ROLLING_WINDOWS) -> pl.DataFrame:
    """
    计算滚动波动率因子

    因子:
    - *_vol_{window}: 多窗口滚动波动率

    Args:
        df: 已包含相关基础列与 ofi 的数据框
        windows: 滚动窗口列表，默认 [60, 180, 360]

    Returns:
        添加了滚动波动率因子的数据框
    """
    logger.info(f"开始计算滚动波动率因子 (windows={windows})")

    volatility_exprs = []
    for window in windows:
        volatility_exprs.extend([
            pl.col("log_return_wap_2").rolling_std(window_size=window).alias(f"log_return_wap_2_vol_{window}"),
            pl.col("log_return_bid1_price").rolling_std(window_size=window).alias(f"log_return_bid1_price_vol_{window}"),
            pl.col("price_spread").rolling_std(window_size=window).alias(f"price_spread_vol_{window}"),
            pl.col("ofi").rolling_std(window_size=window).alias(f"ofi_vol_{window}"),
        ])

    df = df.with_columns(volatility_exprs)

    logger.info("滚动波动率因子计算完成")
    logger.warning(f"注意：前 {max(windows)} 行的滚动波动率因子可能为 null（滚动窗口不足）")
    return df


def calculate_book_shape_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算盘口斜率和凸性因子

    因子:
    - bid_depth_slope / ask_depth_slope: 五档累计深度相对价格距离的线性拟合斜率
    - bid_book_convexity / ask_book_convexity: 归一化累计深度曲线相对对角线的平均偏离

    Args:
        df: 包含五档价格和数量的数据框

    Returns:
        添加了盘口形状因子的数据框
    """
    logger.info("开始计算盘口斜率/凸性因子")

    bid_total = (
        pl.col("bid1_size") + pl.col("bid2_size") + pl.col("bid3_size") + pl.col("bid4_size") + pl.col("bid5_size")
    )
    ask_total = (
        pl.col("ask1_size") + pl.col("ask2_size") + pl.col("ask3_size") + pl.col("ask4_size") + pl.col("ask5_size")
    )

    bid_dist_5 = (pl.col("bid1_price") - pl.col("bid5_price"))
    ask_dist_5 = (pl.col("ask5_price") - pl.col("ask1_price"))

    bid_x = [
        pl.lit(0.0),
        (pl.col("bid1_price") - pl.col("bid2_price")) / (bid_dist_5 + 1e-8),
        (pl.col("bid1_price") - pl.col("bid3_price")) / (bid_dist_5 + 1e-8),
        (pl.col("bid1_price") - pl.col("bid4_price")) / (bid_dist_5 + 1e-8),
        (pl.col("bid1_price") - pl.col("bid5_price")) / (bid_dist_5 + 1e-8),
    ]
    ask_x = [
        pl.lit(0.0),
        (pl.col("ask2_price") - pl.col("ask1_price")) / (ask_dist_5 + 1e-8),
        (pl.col("ask3_price") - pl.col("ask1_price")) / (ask_dist_5 + 1e-8),
        (pl.col("ask4_price") - pl.col("ask1_price")) / (ask_dist_5 + 1e-8),
        (pl.col("ask5_price") - pl.col("ask1_price")) / (ask_dist_5 + 1e-8),
    ]

    bid_y = [
        pl.col("bid1_size") / (bid_total + 1e-8),
        (pl.col("bid1_size") + pl.col("bid2_size")) / (bid_total + 1e-8),
        (pl.col("bid1_size") + pl.col("bid2_size") + pl.col("bid3_size")) / (bid_total + 1e-8),
        (pl.col("bid1_size") + pl.col("bid2_size") + pl.col("bid3_size") + pl.col("bid4_size")) / (bid_total + 1e-8),
        pl.lit(1.0),
    ]
    ask_y = [
        pl.col("ask1_size") / (ask_total + 1e-8),
        (pl.col("ask1_size") + pl.col("ask2_size")) / (ask_total + 1e-8),
        (pl.col("ask1_size") + pl.col("ask2_size") + pl.col("ask3_size")) / (ask_total + 1e-8),
        (pl.col("ask1_size") + pl.col("ask2_size") + pl.col("ask3_size") + pl.col("ask4_size")) / (ask_total + 1e-8),
        pl.lit(1.0),
    ]

    bid_sum_x = sum(bid_x[1:], bid_x[0])
    ask_sum_x = sum(ask_x[1:], ask_x[0])
    bid_sum_y = sum(bid_y[1:], bid_y[0])
    ask_sum_y = sum(ask_y[1:], ask_y[0])
    bid_sum_xy = sum((x * y for x, y in zip(bid_x, bid_y)), pl.lit(0.0))
    ask_sum_xy = sum((x * y for x, y in zip(ask_x, ask_y)), pl.lit(0.0))
    bid_sum_x2 = sum((x * x for x in bid_x), pl.lit(0.0))
    ask_sum_x2 = sum((x * x for x in ask_x), pl.lit(0.0))
    bid_convexity_raw = sum((y - x for x, y in zip(bid_x, bid_y)), pl.lit(0.0)) / 5.0
    ask_convexity_raw = sum((y - x for x, y in zip(ask_x, ask_y)), pl.lit(0.0)) / 5.0

    bid_slope_denominator = 5 * bid_sum_x2 - bid_sum_x * bid_sum_x
    ask_slope_denominator = 5 * ask_sum_x2 - ask_sum_x * ask_sum_x
    bid_shape_valid = (bid_dist_5 > 0) & (bid_total > 0)
    ask_shape_valid = (ask_dist_5 > 0) & (ask_total > 0)

    df = df.with_columns([
        pl.when(bid_shape_valid & (bid_slope_denominator.abs() > 1e-8))
        .then((5 * bid_sum_xy - bid_sum_x * bid_sum_y) / bid_slope_denominator)
        .otherwise(0.0)
        .alias("bid_depth_slope"),
        pl.when(ask_shape_valid & (ask_slope_denominator.abs() > 1e-8))
        .then((5 * ask_sum_xy - ask_sum_x * ask_sum_y) / ask_slope_denominator)
        .otherwise(0.0)
        .alias("ask_depth_slope"),
        pl.when(bid_shape_valid)
        .then(bid_convexity_raw)
        .otherwise(0.0)
        .alias("bid_book_convexity"),
        pl.when(ask_shape_valid)
        .then(ask_convexity_raw)
        .otherwise(0.0)
        .alias("ask_book_convexity"),
    ])

    df = df.with_columns([
        (pl.col("bid_depth_slope") - pl.col("ask_depth_slope")).alias("depth_slope_diff"),
        (pl.col("bid_book_convexity") - pl.col("ask_book_convexity")).alias("book_convexity_diff"),
    ])

    logger.info("盘口斜率/凸性因子计算完成")
    return df


def calculate_liquidity_resilience_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算流动性韧性因子

    因子:
    - spread_recovery: 买卖价差相对上一快照的回落速度
    - bid_gap_recovery / ask_gap_recovery: 双边最大缺档相对上一快照的回补速度
    - bid_depth_replenishment / ask_depth_replenishment: 双边挂单深度回补比例
    - depth_replenishment_diff: 买卖两侧深度回补差
    """
    logger.info("开始计算流动性韧性因子")

    group_keys = _group_keys(df)
    prev_price_spread = _shift_within_groups(pl.col("price_spread"), 1, group_keys)
    prev_max_bid_gap = _shift_within_groups(pl.col("max_bid_gap"), 1, group_keys)
    prev_max_ask_gap = _shift_within_groups(pl.col("max_ask_gap"), 1, group_keys)
    prev_buy_volume = _shift_within_groups(pl.col("buy_volume"), 1, group_keys)
    prev_sell_volume = _shift_within_groups(pl.col("sell_volume"), 1, group_keys)

    df = df.with_columns([
        ((prev_price_spread - pl.col("price_spread")) / (prev_price_spread.abs() + 1e-8))
        .fill_null(0.0)
        .alias("spread_recovery"),
        ((prev_max_bid_gap - pl.col("max_bid_gap")) / (prev_max_bid_gap.abs() + 1e-8))
        .fill_null(0.0)
        .alias("bid_gap_recovery"),
        ((prev_max_ask_gap - pl.col("max_ask_gap")) / (prev_max_ask_gap.abs() + 1e-8))
        .fill_null(0.0)
        .alias("ask_gap_recovery"),
        ((pl.col("buy_volume") - prev_buy_volume) / (prev_buy_volume.abs() + 1e-8))
        .fill_null(0.0)
        .alias("bid_depth_replenishment"),
        ((pl.col("sell_volume") - prev_sell_volume) / (prev_sell_volume.abs() + 1e-8))
        .fill_null(0.0)
        .alias("ask_depth_replenishment"),
    ])

    df = df.with_columns(
        (pl.col("bid_depth_replenishment") - pl.col("ask_depth_replenishment")).alias("depth_replenishment_diff")
    )

    logger.info("流动性韧性因子计算完成")
    return df


def calculate_dynamic_microstructure_features(df: pl.DataFrame, windows: list[int] = ROLLING_WINDOWS) -> pl.DataFrame:
    """
    计算动态盘口微观结构因子

    因子:
    - imbalance_top3_change: 三档不平衡的一阶变化
    - weighted_imbalance_inv_change: 近端加权不平衡的一阶变化
    - ofi_zscore_{window}: ofi 的多窗口滚动标准化
    - bid_depth_slope_change / ask_depth_slope_change: 盘口斜率的一阶变化

    Args:
        df: 已包含不平衡、OFI、盘口形状因子的数据框
        windows: 滚动窗口列表，默认 [60, 180, 360]

    Returns:
        添加了动态盘口微观结构因子的数据框
    """
    logger.info(f"开始计算动态盘口微观结构因子 (windows={windows})")

    dynamic_exprs = [
        (pl.col("imbalance_top3") - pl.col("imbalance_top3").shift(1)).alias("imbalance_top3_change"),
        (pl.col("weighted_imbalance_inv") - pl.col("weighted_imbalance_inv").shift(1)).alias("weighted_imbalance_inv_change"),
        (pl.col("bid_depth_slope") - pl.col("bid_depth_slope").shift(1)).alias("bid_depth_slope_change"),
        (pl.col("ask_depth_slope") - pl.col("ask_depth_slope").shift(1)).alias("ask_depth_slope_change"),
    ]
    for window in windows:
        ofi_rolling_mean = pl.col("ofi").rolling_mean(window_size=window)
        ofi_rolling_std = pl.col("ofi").rolling_std(window_size=window)
        dynamic_exprs.append(
            ((pl.col("ofi") - ofi_rolling_mean) / (ofi_rolling_std + 1e-8)).alias(f"ofi_zscore_{window}")
        )

    df = df.with_columns(dynamic_exprs)

    logger.info("动态盘口微观结构因子计算完成")
    logger.warning(f"注意：前 1 行的 change 因子与前 {max(windows)} 行的 ofi_zscore 因子可能为 null")
    return df


def calculate_trade_rolling_features(df: pl.DataFrame, windows: list[int] = ROLLING_WINDOWS) -> pl.DataFrame:
    """
    计算基于成交/持仓快照衍生量的滚动波动率与窗口斜率因子。

    因子:
    - trade_volume_delta_vol_{w}
    - turnover_delta_vol_{w}
    - avg_trade_price_bias_vol_{w}
    - open_interest_change_vol_{w}
    - trade_volume_delta_zscore_{w}
    - turnover_delta_zscore_{w}
    - avg_trade_price_bias_zscore_{w}
    - avg_trade_price_mid_bias_zscore_{w}
    - open_interest_change_zscore_{w}
    - signed_trade_pressure_{w}
    - signed_open_interest_pressure_{w}
    - trade_ofi_resonance_{w}
    - trade_volume_delta_slope_{w}
    - turnover_delta_slope_{w}
    - avg_trade_price_bias_slope_{w}
    - open_interest_slope_{w}
    """
    logger.info(f"开始计算成交与持仓滚动因子 (windows={windows})")

    group_keys = _group_keys(df)
    trade_direction = (
        pl.when(pl.col("avg_trade_price_bias") > 0)
        .then(1.0)
        .when(pl.col("avg_trade_price_bias") < 0)
        .then(-1.0)
        .otherwise(0.0)
    )
    exprs: list[pl.Expr] = [
        (pl.col("open_interest_change_per_trade") * pl.col("log_return_wap_1")).alias("open_interest_price_link")
    ]
    for window in windows:
        trade_volume_delta_mean = pl.col("trade_volume_delta").rolling_mean(window_size=window)
        trade_volume_delta_std = pl.col("trade_volume_delta").rolling_std(window_size=window)
        turnover_delta_mean = pl.col("turnover_delta").rolling_mean(window_size=window)
        turnover_delta_std = pl.col("turnover_delta").rolling_std(window_size=window)
        avg_trade_price_bias_mean = pl.col("avg_trade_price_bias").rolling_mean(window_size=window)
        avg_trade_price_bias_std = pl.col("avg_trade_price_bias").rolling_std(window_size=window)
        avg_trade_price_mid_bias_mean = pl.col("avg_trade_price_mid_bias").rolling_mean(window_size=window)
        avg_trade_price_mid_bias_std = pl.col("avg_trade_price_mid_bias").rolling_std(window_size=window)
        open_interest_change_mean = pl.col("open_interest_change").rolling_mean(window_size=window)
        open_interest_change_std = pl.col("open_interest_change").rolling_std(window_size=window)
        trade_volume_delta_zscore = (
            (pl.col("trade_volume_delta") - trade_volume_delta_mean) / (trade_volume_delta_std + 1e-8)
        )
        turnover_delta_zscore = (
            (pl.col("turnover_delta") - turnover_delta_mean) / (turnover_delta_std + 1e-8)
        )
        avg_trade_price_bias_zscore = (
            (pl.col("avg_trade_price_bias") - avg_trade_price_bias_mean) / (avg_trade_price_bias_std + 1e-8)
        )
        avg_trade_price_mid_bias_zscore = (
            (pl.col("avg_trade_price_mid_bias") - avg_trade_price_mid_bias_mean) / (avg_trade_price_mid_bias_std + 1e-8)
        )
        open_interest_change_zscore = (
            (pl.col("open_interest_change") - open_interest_change_mean) / (open_interest_change_std + 1e-8)
        )
        exprs.extend([
            trade_volume_delta_std.alias(f"trade_volume_delta_vol_{window}"),
            turnover_delta_std.alias(f"turnover_delta_vol_{window}"),
            avg_trade_price_bias_std.alias(f"avg_trade_price_bias_vol_{window}"),
            open_interest_change_std.alias(f"open_interest_change_vol_{window}"),
            trade_volume_delta_zscore.alias(f"trade_volume_delta_zscore_{window}"),
            turnover_delta_zscore.alias(f"turnover_delta_zscore_{window}"),
            avg_trade_price_bias_zscore.alias(f"avg_trade_price_bias_zscore_{window}"),
            avg_trade_price_mid_bias_zscore.alias(f"avg_trade_price_mid_bias_zscore_{window}"),
            open_interest_change_zscore.alias(f"open_interest_change_zscore_{window}"),
            (trade_direction * trade_volume_delta_zscore).alias(f"signed_trade_pressure_{window}"),
            (trade_direction * open_interest_change_zscore).alias(f"signed_open_interest_pressure_{window}"),
            (avg_trade_price_bias_zscore * pl.col(f"ofi_zscore_{window}")).alias(f"trade_ofi_resonance_{window}"),
            _endpoint_slope_expr("trade_volume_delta", window, group_keys),
            _endpoint_slope_expr("turnover_delta", window, group_keys),
            _endpoint_slope_expr("avg_trade_price_bias", window, group_keys),
            _endpoint_slope_expr("open_interest", window, group_keys),
        ])

    df = df.with_columns(exprs)

    logger.info("成交与持仓滚动因子计算完成")
    logger.warning(f"注意：前 {max(windows)} 行的成交/持仓滚动因子可能为 null（滚动窗口不足）")
    return df


# ==================== 趋势因子 ====================
def calculate_trend_features(df: pl.DataFrame, windows: list[int] = ROLLING_WINDOWS) -> pl.DataFrame:
    """
    计算趋势因子 (标准化趋势)

    公式: y_trend = (y - RollingMean(y, window)) / RollingStd(y, window)

    因子列表:
    - *_trend_{window}

    注意：前 window 行数据会有 null 值（滚动窗口不足）

    Args:
        df: 包含基础因子的数据框
        windows: 滚动窗口列表，默认 [60, 180, 360]

    Returns:
        添加了趋势因子的数据框
    """
    logger.info(f"开始计算趋势因子 (windows={windows})")

    # 需要计算趋势的列
    base_columns = [
        "ask1_price",
        "bid1_price",
        "buy_spread",
        "sell_spread",
        "wap_1",
        "wap_2",
        "buy_vwap",
        "sell_vwap",
        "volume"
    ]

    trend_exprs = []
    for window in windows:
        for col in base_columns:
            rolling_mean = pl.col(col).rolling_mean(window_size=window)
            rolling_std = pl.col(col).rolling_std(window_size=window)
            trend_exprs.append(
                ((pl.col(col) - rolling_mean) / (rolling_std + 1e-8)).alias(f"{col}_trend_{window}")
            )

    df = df.with_columns(trend_exprs)

    logger.info("趋势因子计算完成")
    logger.warning(f"注意：前 {max(windows)} 行的趋势因子可能为 null（滚动窗口不足）")

    return df


def calculate_relative_and_regime_features(
    df: pl.DataFrame,
    windows: list[int] = RELATIVE_WINDOWS,
) -> pl.DataFrame:
    """
    计算相对化与市场状态（regime）因子。

    设计目标：
    - 将绝对价格/量能映射到滚动相对值，降低跨阶段价格中枢变化带来的漂移
    - 构造跨窗口状态比值，识别“当前档位”是否较历史更活跃、更波动

    因子:
    - *_zscore_{w}: 滚动标准化
    - *_ratio_{w}: 当前值相对滚动均值
    - vol_regime_ratio_20_60 / vol_regime_ratio_60_180 / vol_regime_ratio_60_360
    - volume_regime_ratio_60_360 / turnover_regime_ratio_60_360 / spread_regime_ratio_60_360
    - depth_near_share / depth_near_share_zscore_60 / depth_near_share_zscore_360
    """
    logger.info(f"开始计算相对化与市场状态因子 (windows={windows})")

    zscore_columns = [
        "close_price",
        "wap_1",
        "wap_2",
        "bid1_price",
        "ask1_price",
        "price_spread",
    ]
    ratio_columns = [
        "close_price",
        "wap_1",
        "volume",
        "trade_volume_delta",
        "turnover_delta",
        "open_interest",
        "klen",
    ]

    exprs: list[pl.Expr] = []
    for window in windows:
        for column in zscore_columns:
            exprs.append(_rolling_zscore_expr(column, window, f"{column}_zscore_{window}"))
        for column in ratio_columns:
            exprs.append(_rolling_ratio_expr(column, window, f"{column}_ratio_{window}"))

    rv_20 = pl.col("log_return_wap_1").rolling_std(window_size=20)
    rv_60 = pl.col("log_return_wap_1").rolling_std(window_size=60)
    rv_180 = pl.col("log_return_wap_1").rolling_std(window_size=180)
    rv_360 = pl.col("log_return_wap_1").rolling_std(window_size=360)
    volume_mean_60 = pl.col("trade_volume_delta").rolling_mean(window_size=60)
    volume_mean_360 = pl.col("trade_volume_delta").rolling_mean(window_size=360)
    turnover_mean_60 = pl.col("turnover_delta").rolling_mean(window_size=60)
    turnover_mean_360 = pl.col("turnover_delta").rolling_mean(window_size=360)
    spread_mean_60 = pl.col("price_spread").rolling_mean(window_size=60)
    spread_mean_360 = pl.col("price_spread").rolling_mean(window_size=360)
    depth_near_share = (
        (pl.col("bid1_size") + pl.col("ask1_size"))
        / (pl.col("buy_volume") + pl.col("sell_volume") + 1e-8)
    )
    depth_near_mean_60 = depth_near_share.rolling_mean(window_size=60)
    depth_near_std_60 = depth_near_share.rolling_std(window_size=60)
    depth_near_mean_360 = depth_near_share.rolling_mean(window_size=360)
    depth_near_std_360 = depth_near_share.rolling_std(window_size=360)

    exprs.extend([
        (rv_20 / (rv_60 + 1e-8)).alias("vol_regime_ratio_20_60"),
        (rv_60 / (rv_180 + 1e-8)).alias("vol_regime_ratio_60_180"),
        (rv_60 / (rv_360 + 1e-8)).alias("vol_regime_ratio_60_360"),
        (volume_mean_60 / (volume_mean_360 + 1e-8)).alias("volume_regime_ratio_60_360"),
        (turnover_mean_60 / (turnover_mean_360 + 1e-8)).alias("turnover_regime_ratio_60_360"),
        (spread_mean_60 / (spread_mean_360 + 1e-8)).alias("spread_regime_ratio_60_360"),
        depth_near_share.alias("depth_near_share"),
        ((depth_near_share - depth_near_mean_60) / (depth_near_std_60 + 1e-8)).alias("depth_near_share_zscore_60"),
        ((depth_near_share - depth_near_mean_360) / (depth_near_std_360 + 1e-8)).alias("depth_near_share_zscore_360"),
    ])

    df = df.with_columns(exprs)

    logger.info("相对化与市场状态因子计算完成")
    logger.warning(f"注意：前 {max(windows + [360])} 行的相对化/状态因子可能为 null（滚动窗口不足）")
    return df


# ==================== 主计算函数 ====================
def calculate_all_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算所有因子

    执行顺序:
    1. K线特征因子
    2. 归一化订单量
    3. WAP因子
    4. 成交与持仓快照衍生因子
    5. 价差因子
    6. 缺档因子
    7. 成交量因子
    8. 分层不平衡与队列集中度因子
    9. VWAP因子
    10. 对数收益率因子
    11. 稳定性因子
    12. 订单流失衡因子
    13. 滚动波动率因子
    14. 盘口斜率/凸性因子
    15. 流动性韧性因子
    16. 动态盘口微观结构因子
    17. 成交与持仓滚动因子
    18. 趋势因子
    19. 相对化与市场状态因子

    Args:
        df: 合并后的原始数据（包含K线和订单簿数据）

    Returns:
        包含所有因子的数据框
    """
    logger.info("="*60)
    logger.info("开始计算所有因子")
    logger.info("="*60)

    original_rows = len(df)
    original_cols = len(df.columns)

    # 1. K线特征
    df = calculate_kline_features(df)

    # 2. 归一化订单量
    df = calculate_volume_and_normalized_size(df)

    # 3. WAP 因子
    df = calculate_wap_features(df)

    # 4. 成交与持仓快照衍生因子
    df = calculate_trade_snapshot_features(df)

    # 5. 价差因子
    df = calculate_spread_features(df)

    # 6. 缺档因子
    df = calculate_gap_features(df)

    # 7. 成交量因子
    df = calculate_volume_features(df)

    # 8. 分层不平衡与队列集中度因子
    df = calculate_depth_balance_features(df)

    # 9. VWAP 因子
    df = calculate_vwap_features(df)

    # 10. 对数收益率因子
    df = calculate_log_return_features(df)

    # 11. 稳定性因子
    df = calculate_stability_features(df)

    # 12. 订单流失衡因子
    df = calculate_order_flow_features(df)

    # 13. 滚动波动率因子
    df = calculate_volatility_features(df)

    # 14. 盘口斜率/凸性因子
    df = calculate_book_shape_features(df)

    # 15. 流动性韧性因子
    df = calculate_liquidity_resilience_features(df)

    # 16. 动态盘口微观结构因子
    df = calculate_dynamic_microstructure_features(df)

    # 17. 成交与持仓滚动因子
    df = calculate_trade_rolling_features(df)

    # 18. 趋势因子
    df = calculate_trend_features(df)

    # 19. 相对化与市场状态因子
    df = calculate_relative_and_regime_features(df)

    final_rows = len(df)
    final_cols = len(df.columns)

    logger.info("="*60)
    logger.info("所有因子计算完成")
    logger.info(f"数据行数: {original_rows} -> {final_rows}")
    logger.info(f"数据列数: {original_cols} -> {final_cols}")
    logger.info(f"新增因子数: {final_cols - original_cols}")
    logger.info("="*60)

    return df


def get_feature_columns() -> List[str]:
    """
    获取所有因子列名（按类别排序）

    Returns:
        因子列名列表
    """
    return [
        # K线特征因子
        "kmid", "kmid2", "klen", "kup", "kup2", "klow", "klow2", "ksft", "ksft2",

        # 归一化订单量（包含volume）
        "volume",
        "bid1_size_n", "bid2_size_n", "bid3_size_n", "bid4_size_n", "bid5_size_n",
        "ask1_size_n", "ask2_size_n", "ask3_size_n", "ask4_size_n", "ask5_size_n",

        # WAP因子
        "wap_1", "wap_2", "wap_balance",

        # 价差因子
        "buy_spread", "sell_spread", "price_spread",

        # 缺档因子
        "bid_gap_1_2", "bid_gap_2_3", "bid_gap_3_4", "bid_gap_4_5",
        "ask_gap_1_2", "ask_gap_2_3", "ask_gap_3_4", "ask_gap_4_5",
        "bid_gap_count", "max_bid_gap", "bid_gap_near_far_ratio",
        "ask_gap_count", "max_ask_gap", "ask_gap_near_far_ratio",
        "gap_count_diff", "max_gap_diff", "gap_near_far_ratio_diff",

        # 成交量因子
        "buy_volume", "sell_volume", "volume_imbalance",

        # 分层不平衡与队列集中度因子
        "imbalance_top1", "imbalance_top3", "imbalance_top5",
        "weighted_imbalance_inv",
        "bid1_queue_concentration", "ask1_queue_concentration",
        "top2_depth_share",

        # 成交与持仓快照衍生因子
        "trade_volume_delta", "turnover_delta",
        "avg_trade_price", "avg_trade_price_bias", "avg_trade_price_mid_bias", "avg_trade_price_bias_change",
        "open_interest_change", "open_interest_change_ratio",
        "open_interest_change_per_trade", "open_interest_price_link",

        # VWAP因子
        "buy_vwap", "sell_vwap",

        # 对数收益率因子
        "log_return_bid1_price", "log_return_bid2_price",
        "log_return_ask1_price", "log_return_ask2_price",
        "log_return_wap_1", "log_return_wap_2",

        # 稳定性因子
        "best_spread_duration", "best_quote_duration",
        *[f"log_return_wap_1_vol_{window}" for window in ROLLING_WINDOWS],

        # 流动性韧性因子
        "spread_recovery",
        "bid_gap_recovery", "ask_gap_recovery",
        "bid_depth_replenishment", "ask_depth_replenishment",
        "depth_replenishment_diff",

        # 订单流失衡因子
        "ofi", *[f"ofi_{window}" for window in ROLLING_WINDOWS],

        # 波动率因子
        *[f"log_return_wap_2_vol_{window}" for window in ROLLING_WINDOWS],
        *[f"log_return_bid1_price_vol_{window}" for window in ROLLING_WINDOWS],
        *[f"price_spread_vol_{window}" for window in ROLLING_WINDOWS],
        *[f"ofi_vol_{window}" for window in ROLLING_WINDOWS],

        # 盘口斜率/凸性因子
        "bid_depth_slope", "ask_depth_slope",
        "bid_book_convexity", "ask_book_convexity",
        "depth_slope_diff", "book_convexity_diff",

        # 动态盘口微观结构因子
        "imbalance_top3_change", "weighted_imbalance_inv_change",
        *[f"ofi_zscore_{window}" for window in ROLLING_WINDOWS],
        "bid_depth_slope_change", "ask_depth_slope_change",

        # 成交与持仓滚动因子
        *[f"trade_volume_delta_vol_{window}" for window in ROLLING_WINDOWS],
        *[f"turnover_delta_vol_{window}" for window in ROLLING_WINDOWS],
        *[f"avg_trade_price_bias_vol_{window}" for window in ROLLING_WINDOWS],
        *[f"open_interest_change_vol_{window}" for window in ROLLING_WINDOWS],
        *[f"trade_volume_delta_zscore_{window}" for window in ROLLING_WINDOWS],
        *[f"turnover_delta_zscore_{window}" for window in ROLLING_WINDOWS],
        *[f"avg_trade_price_bias_zscore_{window}" for window in ROLLING_WINDOWS],
        *[f"avg_trade_price_mid_bias_zscore_{window}" for window in ROLLING_WINDOWS],
        *[f"open_interest_change_zscore_{window}" for window in ROLLING_WINDOWS],
        *[f"signed_trade_pressure_{window}" for window in ROLLING_WINDOWS],
        *[f"signed_open_interest_pressure_{window}" for window in ROLLING_WINDOWS],
        *[f"trade_ofi_resonance_{window}" for window in ROLLING_WINDOWS],
        *[f"trade_volume_delta_slope_{window}" for window in ROLLING_WINDOWS],
        *[f"turnover_delta_slope_{window}" for window in ROLLING_WINDOWS],
        *[f"avg_trade_price_bias_slope_{window}" for window in ROLLING_WINDOWS],
        *[f"open_interest_slope_{window}" for window in ROLLING_WINDOWS],

        # 趋势因子
        *[
            f"{col}_trend_{window}"
            for window in ROLLING_WINDOWS
            for col in [
                "ask1_price", "bid1_price", "buy_spread", "sell_spread",
                "wap_1", "wap_2", "buy_vwap", "sell_vwap", "volume"
            ]
        ],

        # 相对化与市场状态因子
        *[
            f"{col}_zscore_{window}"
            for window in RELATIVE_WINDOWS
            for col in [
                "close_price", "wap_1", "wap_2", "bid1_price", "ask1_price", "price_spread"
            ]
        ],
        *[
            f"{col}_ratio_{window}"
            for window in RELATIVE_WINDOWS
            for col in [
                "close_price", "wap_1", "volume",
                "trade_volume_delta", "turnover_delta", "open_interest", "klen"
            ]
        ],
        "vol_regime_ratio_20_60",
        "vol_regime_ratio_60_180",
        "vol_regime_ratio_60_360",
        "volume_regime_ratio_60_360",
        "turnover_regime_ratio_60_360",
        "spread_regime_ratio_60_360",
        "depth_near_share",
        "depth_near_share_zscore_60",
        "depth_near_share_zscore_360",
    ]


# ==================== 测试代码 ====================
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建测试数据
    print("\n" + "="*60)
    print("创建测试数据")
    print("="*60)

    test_data = {
        "timestamp": ["2023-06-30 00:00:00", "2023-06-30 00:01:00", "2023-06-30 00:02:00"],
        "date": ["2023-06-30", "2023-06-30", "2023-06-30"],
        "contract": ["al_demo", "al_demo", "al_demo"],
        "open_price": [2951.21, 2951.75, 2951.81],
        "high_price": [2952.54, 2952.44, 2951.81],
        "low_price": [2950.59, 2951.44, 2947.77],
        "close_price": [2951.76, 2951.80, 2949.54],
        "total_trade_volume": [1280.0, 1295.0, 1330.0],
        "turnover": [82027275.0, 82170510.0, 82504180.0],
        "open_interest": [195258.0, 195264.0, 195240.0],
        "bid1_price": [5.445, 5.446, 5.447],
        "bid1_size": [532488, 532500, 532600],
        "bid2_price": [5.440, 5.441, 5.442],
        "bid2_size": [820210, 820300, 820400],
        "bid3_price": [5.435, 5.436, 5.437],
        "bid3_size": [870330, 870400, 870500],
        "bid4_price": [5.430, 5.431, 5.432],
        "bid4_size": [886610, 886700, 886800],
        "bid5_price": [5.425, 5.426, 5.427],
        "bid5_size": [894475, 894500, 894600],
        "ask1_price": [5.455, 5.456, 5.457],
        "ask1_size": [523344, 523400, 523500],
        "ask2_price": [5.460, 5.461, 5.462],
        "ask2_size": [877736, 877800, 877900],
        "ask3_price": [5.465, 5.466, 5.467],
        "ask3_size": [989833, 989900, 990000],
        "ask4_price": [5.470, 5.471, 5.472],
        "ask4_size": [1008206, 1008300, 1008400],
        "ask5_price": [5.475, 5.476, 5.477],
        "ask5_size": [1015844, 1015900, 1016000]
    }

    df = pl.DataFrame(test_data)
    print(f"测试数据形状: {df.shape}")
    print(f"列名: {df.columns}")

    # 测试所有因子计算
    print("\n" + "="*60)
    print("测试因子计算")
    print("="*60)

    result = calculate_all_features(df)

    print(f"\n结果数据形状: {result.shape}")
    print(f"\n前3行数据:")
    print(result.head(3))

    print(f"\n所有列名:")
    for i, col in enumerate(result.columns, 1):
        print(f"{i:2d}. {col}")

    print(f"\n因子列表:")
    feature_cols = get_feature_columns()
    for i, col in enumerate(feature_cols, 1):
        print(f"{i:2d}. {col}")

    print(f"\n总因子数: {len(feature_cols)}")
