"""
因子计算模块
实现所有因子的计算逻辑
"""

import polars as pl
import numpy as np
import logging
from typing import List

logger = logging.getLogger(__name__)


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


# ==================== 趋势因子 ====================
def calculate_trend_features(df: pl.DataFrame, window: int = 60) -> pl.DataFrame:
    """
    计算趋势因子 (标准化趋势)

    公式: y_trend = (y - RollingMean(y, window)) / RollingStd(y, window)

    因子列表:
    - ask1_price_trend_60
    - bid1_price_trend_60
    - buy_spread_trend_60
    - sell_spread_trend_60
    - wap_1_trend_60
    - wap_2_trend_60
    - buy_vwap_trend_60
    - sell_vwap_trend_60
    - volume_trend_60

    注意：前 window 行数据会有 null 值（滚动窗口不足）

    Args:
        df: 包含基础因子的数据框
        window: 滚动窗口大小，默认60

    Returns:
        添加了趋势因子的数据框
    """
    logger.info(f"开始计算趋势因子 (window={window})")

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
    for col in base_columns:
        # 计算滚动均值和标准差
        rolling_mean = pl.col(col).rolling_mean(window_size=window)
        rolling_std = pl.col(col).rolling_std(window_size=window)

        # 计算趋势因子: (y - rolling_mean) / rolling_std
        trend = ((pl.col(col) - rolling_mean) / rolling_std).alias(f"{col}_trend_{window}")
        trend_exprs.append(trend)

    df = df.with_columns(trend_exprs)

    logger.info("趋势因子计算完成")
    logger.warning(f"注意：前 {window} 行的趋势因子可能为 null（滚动窗口不足）")

    return df


# ==================== 主计算函数 ====================
def calculate_all_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    计算所有因子

    执行顺序:
    1. K线特征因子
    2. 归一化订单量
    3. WAP因子
    4. 价差因子
    5. 成交量因子
    6. VWAP因子
    7. 对数收益率因子
    8. 趋势因子

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

    # 4. 价差因子
    df = calculate_spread_features(df)

    # 5. 成交量因子
    df = calculate_volume_features(df)

    # 6. VWAP 因子
    df = calculate_vwap_features(df)

    # 7. 对数收益率因子
    df = calculate_log_return_features(df)

    # 8. 趋势因子
    df = calculate_trend_features(df)

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

        # 成交量因子
        "buy_volume", "sell_volume", "volume_imbalance",

        # VWAP因子
        "buy_vwap", "sell_vwap",

        # 对数收益率因子
        "log_return_bid1_price", "log_return_bid2_price",
        "log_return_ask1_price", "log_return_ask2_price",
        "log_return_wap_1", "log_return_wap_2",

        # 趋势因子
        "ask1_price_trend_60", "bid1_price_trend_60",
        "buy_spread_trend_60", "sell_spread_trend_60",
        "wap_1_trend_60", "wap_2_trend_60",
        "buy_vwap_trend_60", "sell_vwap_trend_60",
        "volume_trend_60"
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
        "open_price": [2951.21, 2951.75, 2951.81],
        "high_price": [2952.54, 2952.44, 2951.81],
        "low_price": [2950.59, 2951.44, 2947.77],
        "close_price": [2951.76, 2951.80, 2949.54],
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
