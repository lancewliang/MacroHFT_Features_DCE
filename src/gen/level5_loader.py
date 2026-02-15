"""
五档行情数据加载模块
负责从 DCE CSV 文件中读取五档行情数据，并进行预处理
"""

import polars as pl
from pathlib import Path
from typing import List, Optional
import logging

try:
    # 尝试相对导入（当作为包导入时）
    from .config import (
        get_dce_filepath,
        DATA_TYPE_LEVEL5,
        DCE_RENAME_MAP,
        DCE_KEEP_ORIGINAL
    )
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from config import (
        get_dce_filepath,
        DATA_TYPE_LEVEL5,
        DCE_RENAME_MAP,
        DCE_KEEP_ORIGINAL
    )

# 配置日志
logger = logging.getLogger(__name__)


def load_daily_dce_data(date_str: str, contract_code: str) -> Optional[pl.DataFrame]:
    """
    从 CSV 文件中读取单日DCE五档行情数据

    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        main_contracts: 主力合约列表，例如 ['m2301', 'm2305']

    Returns:
        Polars DataFrame 或 None（如果文件不存在）

    DataFrame 格式:
        - timestamp: 时间戳 (TradingDay + UpdateTime)
       
        - bid1_price ~ bid5_price: 买方五档价格
        - bid1_size ~ bid5_size: 买方五档数量
        - ask1_price ~ ask5_price: 卖方五档价格
        - ask1_size ~ ask5_size: 卖方五档数量
        - contract: 合约代码（当合并多个合约时）
        - 其他原始字段...
    """
    if not contract_code:
        logger.error("contract_code 参数不能为空")
        return None

    # 加载并合并所有合约的数据
  
    csv_path = get_dce_filepath(date_str, contract_code, DATA_TYPE_LEVEL5)

    if not csv_path.exists():
        logger.warning(f"DCE数据文件不存在: {csv_path}")
        return None

    try:
        # 读取CSV文件
        df = pl.read_csv(csv_path)

        # 检查必要的列是否存在
        required_cols = ["TradingDay", "UpdateTime"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"合约 {contract_code} 缺少必要列 {missing_cols}: {csv_path}")
            return None

        # 添加合约代码列
        df = df.with_columns(pl.lit(contract_code).alias("contract"))

        # 添加合约月份列（提取合约代码中的月份部分，只保留月份数字1-12）
        # 合约格式如：m2301 -> 月份为1，i2405 -> 月份为5
        month_str = contract_code[1:]  # 去掉品种代码，保留月份部分
        month_num = int(month_str[-2:])  # 提取最后两位作为月份数字
        df = df.with_columns(pl.lit(month_num).alias("contract_month"))

      
        logger.info(f"成功加载合约数据: {date_str}, 合约: {contract_code}, 行数: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"读取合约数据失败 {date_str}, 合约 {contract_code}: {str(e)}")
        return None
  

def preprocess_dce_data(df: pl.DataFrame) -> pl.DataFrame:
    """
    预处理DCE五档行情数据

    处理步骤:
    1. 创建时间戳 (TradingDay + UpdateTime)
    2. 重命名列 (BidPrice1 -> bid1_price, Volume -> volume_snp, etc.)
    3. 选择需要的列
    4. 按时间戳截断到分钟级别并去重（保留每分钟最后一条）
    5. 计算成交量和成交额增量（trade_volume1, trade_turnover1）

    注意:
    - volume_snp 和 turnover_snp 是快照数据（累计值）
    - trade_volume1 和 trade_turnover1 是每分钟的增量（当前分钟 - 上一分钟）

    Args:
        df: 原始DCE数据

    Returns:
        预处理后的数据，包含增量字段
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

    # 3. 按合约和时间戳排序（从早到晚）
    df = df.sort("timestamp")

    # 4. 按时间窗口截断时间戳到分钟级别
    df = df.with_columns(
        pl.col("timestamp").dt.truncate("1m").alias("minute")
    )

    # 5. 按分钟分组聚合（使用1分钟内的所有记录）
    # 订单簿列（已重命名）
    orderbook_columns = []
    for i in range(1, 6):
        orderbook_columns.extend([
            f"bid{i}_price", f"bid{i}_size",
            f"ask{i}_price", f"ask{i}_size"
        ])

    # 构建聚合表达式
    agg_exprs = []

    # 保留 contract_month（取第一个值）
    if "contract_month" in df.columns:
        agg_exprs.append(pl.col("contract_month").first().alias("contract_month"))

    # 订单簿数据：取每分钟最后一条（快照值）
    for col in orderbook_columns:
        if col in df.columns:
            agg_exprs.append(pl.col(col).last().alias(col))

    # 成交量和成交额快照：取每分钟最后一条
    if "volume_snp" in df.columns:
        agg_exprs.append(pl.col("volume_snp").last().alias("volume_snp"))
    if "turnover_snp" in df.columns:
        agg_exprs.append(pl.col("turnover_snp").last().alias("turnover_snp"))

    # 保留的原始列：取最后一条
    for col in DCE_KEEP_ORIGINAL:
        if col in df.columns:
            agg_exprs.append(pl.col(col).last().alias(col))

    # 执行分组聚合
    df_agg = df.group_by("minute").agg(agg_exprs).sort("minute")

    # 6. 计算每分钟的成交量和成交额增量
    # volume_snp 和 turnover_snp 是快照数据（累计值），需要计算增量
    if "volume_snp" in df_agg.columns:
        # 获取上一分钟的数据
        df_agg = df_agg.with_columns([
            pl.col("minute").shift(1).over("contract").alias("prev_minute") if "contract" in df_agg.columns
            else pl.col("minute").shift(1).alias("prev_minute"),

            pl.col("volume_snp").shift(1).over("contract").alias("prev_volume_snp") if "contract" in df_agg.columns
            else pl.col("volume_snp").shift(1).alias("prev_volume_snp")
        ])

        # 计算期望的上一分钟时间
        df_agg = df_agg.with_columns([
            (pl.col("minute") - pl.duration(minutes=1)).alias("expected_prev_minute")
        ])

        # 只有当上一行确实是上一分钟时，才计算增量；否则设为当前值（第一条记录）
        df_agg = df_agg.with_columns([
            pl.when(pl.col("prev_minute") == pl.col("expected_prev_minute"))
            .then(pl.col("volume_snp") - pl.col("prev_volume_snp"))
            .otherwise(pl.col("volume_snp"))  # 第一条记录使用当前快照值
            .alias("trade_volume1")
        ])

        # 删除临时列
        df_agg = df_agg.drop(["prev_minute", "prev_volume_snp", "expected_prev_minute"])

    if "turnover_snp" in df_agg.columns:
        # 获取上一分钟的数据
        df_agg = df_agg.with_columns([
            pl.col("minute").shift(1).over("contract").alias("prev_minute") if "contract" in df_agg.columns
            else pl.col("minute").shift(1).alias("prev_minute"),

            pl.col("turnover_snp").shift(1).over("contract").alias("prev_turnover_snp") if "contract" in df_agg.columns
            else pl.col("turnover_snp").shift(1).alias("prev_turnover_snp")
        ])

        # 计算期望的上一分钟时间
        df_agg = df_agg.with_columns([
            (pl.col("minute") - pl.duration(minutes=1)).alias("expected_prev_minute")
        ])

        # 只有当上一行确实是上一分钟时，才计算增量；否则设为当前值（第一条记录）
        df_agg = df_agg.with_columns([
            pl.when(pl.col("prev_minute") == pl.col("expected_prev_minute"))
            .then(pl.col("turnover_snp") - pl.col("prev_turnover_snp"))
            .otherwise(pl.col("turnover_snp"))  # 第一条记录使用当前快照值
            .alias("trade_turnover1")
        ])

        # 删除临时列
        df_agg = df_agg.drop(["prev_minute", "prev_turnover_snp", "expected_prev_minute"])

    # 重命名 minute 为 timestamp
    df_agg = df_agg.rename({"minute": "timestamp"})

    final_rows = len(df_agg)

    logger.info(f"DCE数据预处理完成，行数: {original_rows} -> {final_rows} (每分钟聚合1条)")
    if original_rows > final_rows:
        logger.info(f"聚合处理: {original_rows - final_rows} 行")

    # 输出增量计算信息
    if "trade_volume1" in df_agg.columns:
        logger.info("已计算每分钟成交量增量 (trade_volume1)")
    if "trade_turnover1" in df_agg.columns:
        logger.info("已计算每分钟成交额增量 (trade_turnover1)")

    return df_agg
