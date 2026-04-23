"""
主执行脚本
生成高频交易因子特征数据集
"""

import polars as pl
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from typing import Optional

# 导入自定义模块
from config import (
    START_DATE,
    END_DATE,
    BATCH_SIZE_DAYS,
    COMMODITY,
    SYMBOL,
    OUTPUT_FORMAT,
    LOG_LEVEL,
    LOG_FILE,
    LOG_DIR,
    TIMEFRAME,
    ORDERBOOK_REQUIRED_COLUMNS,
    get_output_filepath,
    ensure_directories
)
from data_loader import (
    load_and_merge_date_range,
    generate_date_range
)
from feature_calculator import (
    calculate_all_features,
    get_feature_columns,
    ROLLING_WINDOWS,
    RELATIVE_WINDOWS,
)


def log_pre_drop_data_quality(df: pl.DataFrame, logger: logging.Logger, top_k: int = 20) -> None:
    """
    输出 drop 前的数据质量诊断，帮助定位哪些列在触发大量删行。
    """
    total_rows = len(df)
    if total_rows == 0:
        logger.warning("预清洗诊断: 数据为空，跳过质量分析")
        return

    # 1) null 统计
    null_dict = df.null_count().to_dicts()[0]
    null_items = sorted(
        [(col, int(cnt)) for col, cnt in null_dict.items() if int(cnt) > 0],
        key=lambda x: x[1],
        reverse=True,
    )

    if null_items:
        logger.warning(f"预清洗诊断: 共有 {len(null_items)} 列存在 null")
        logger.warning(f"预清洗诊断: null Top{min(top_k, len(null_items))} 列:")
        for col, cnt in null_items[:top_k]:
            logger.warning(f"  - {col}: {cnt} ({cnt / total_rows:.2%})")
    else:
        logger.info("预清洗诊断: 未发现 null 列")

    # 2) NaN 统计（仅浮点列）
    float_cols = [c for c in df.columns if df[c].dtype in (pl.Float32, pl.Float64)]
    nan_items = []
    if float_cols:
        nan_counts = df.select([pl.col(c).is_nan().sum().alias(c) for c in float_cols]).to_dicts()[0]
        nan_items = sorted(
            [(col, int(cnt)) for col, cnt in nan_counts.items() if int(cnt) > 0],
            key=lambda x: x[1],
            reverse=True,
        )
    if nan_items:
        logger.warning(f"预清洗诊断: 共有 {len(nan_items)} 列存在 NaN")
        logger.warning(f"预清洗诊断: NaN Top{min(top_k, len(nan_items))} 列:")
        for col, cnt in nan_items[:top_k]:
            logger.warning(f"  - {col}: {cnt} ({cnt / total_rows:.2%})")
    else:
        logger.info("预清洗诊断: 未发现 NaN 列")

    # 3) 行级影响（与主流程 drop_nulls 行为一致）
    has_null_rows = df.select(pl.any_horizontal([pl.col(c).is_null() for c in df.columns]).sum()).item()
    logger.info(f"预清洗诊断: 包含至少一个 null 的行数 = {has_null_rows} ({has_null_rows / total_rows:.2%})")

    if float_cols:
        has_nan_rows = df.select(pl.any_horizontal([pl.col(c).is_nan() for c in float_cols]).sum()).item()
        logger.info(f"预清洗诊断: 包含至少一个 NaN 的行数 = {has_nan_rows} ({has_nan_rows / total_rows:.2%})")

 
def drop_warmup_samples(df: pl.DataFrame, logger: logging.Logger) -> pl.DataFrame:
    """
    删除预热样本：按合约剔除前 N 行，其中 N 为当前策略最大滚动窗口。
    """
    # 注意：regime 因子内部仍使用 360 窗口（vol_regime_ratio_60_360 等）
    warmup_window = max(ROLLING_WINDOWS + RELATIVE_WINDOWS + [360])
    if warmup_window <= 0:
        return df

    rows_before = len(df)
    if "contract" in df.columns:
        df = (
            df.with_columns(pl.int_range(0, pl.len()).over("contract").alias("_contract_row_idx"))
            .filter(pl.col("_contract_row_idx") >= warmup_window)
            .drop("_contract_row_idx")
        )
        rows_after = len(df)
        logger.info(f"按合约剔除预热样本: 每个合约前 {warmup_window} 行，共删除 {rows_before - rows_after} 行")
        return df

    df = (
        df.with_row_count("_row_idx")
        .filter(pl.col("_row_idx") >= warmup_window)
        .drop("_row_idx")
    )
    rows_after = len(df)
    logger.info(f"按全局剔除预热样本: 前 {warmup_window} 行，共删除 {rows_before - rows_after} 行")
    return df


def drop_rows_with_feature_nulls(df: pl.DataFrame, logger: logging.Logger) -> pl.DataFrame:
    """
    预热剔除后，进一步删除仍包含特征空值的样本。
    """
    feature_columns = [col for col in get_feature_columns() if col in df.columns]
    if not feature_columns:
        logger.warning("未识别到因子列，跳过因子空值剔除")
        return df

    rows_before = len(df)
    df = df.drop_nulls(subset=feature_columns)
    rows_after = len(df)
    if rows_before > rows_after:
        logger.info(f"删除了 {rows_before - rows_after} 行仍含因子空值的数据")
    return df



def setup_logging(log_file: Optional[Path] = None, level: str = "INFO"):
    """
    配置日志系统

    Args:
        log_file: 日志文件路径
        level: 日志级别
    """
    # 确保日志目录存在
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 配置处理器
    handlers = [logging.StreamHandler()]  # 控制台输出
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))  # 文件输出

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
  

def generate_features_single_file(
    start_date: str,
    end_date: str,
    batch_size: int = BATCH_SIZE_DAYS,
    timeframe: str = TIMEFRAME,
    commodity: str = COMMODITY,
    symbol: str = SYMBOL,
) -> bool:
    """
    生成单个特征文件（分批处理后合并）

    Args:
        start_date: 起始日期
        end_date: 结束日期
        batch_size: 批处理大小（天数）
        timeframe: 时间粒度，如 '30s' 或 '1m'
        commodity: 品种名称，如 '铝' 或 '燃料油'
        symbol: 品种英文符号前缀，如 'al' 或 'fu'

    Returns:
        是否成功
    """
    logger = logging.getLogger(__name__)
    logger.info(
        f"使用单文件策略生成特征 "
        f"(commodity={commodity}, symbol={symbol}, timeframe={timeframe})"
    )

    # 生成日期范围
    all_dates = generate_date_range(start_date, end_date)
    total_days = len(all_dates)

    logger.info(f"总共需要处理 {total_days} 天，批大小 {batch_size} 天")

    # 分批加载原始数据
    raw_dfs = []
    for i in range(0, total_days, batch_size):
        batch_num = i // batch_size + 1
        total_batches = (total_days + batch_size - 1) // batch_size

        batch_start = all_dates[i]
        batch_end_idx = min(i + batch_size, total_days)
        batch_end = all_dates[batch_end_idx - 1]

        logger.info(f"\n加载批次 {batch_num}/{total_batches}: {batch_start} 至 {batch_end}")

        try:
            merged_df = load_and_merge_date_range(
                batch_start,
                batch_end,
                commodity=commodity,
                timeframe=timeframe,
                symbol=symbol,
            )
            if merged_df is None:
                logger.warning(f"批次 {batch_num} 数据加载失败，跳过")
                continue
            raw_dfs.append(merged_df)
            logger.info(f"批次 {batch_num} 加载完成，{len(merged_df)} 行")
        except Exception as e:
            logger.error(f"批次 {batch_num} 加载失败: {str(e)}\n{traceback.format_exc()}")
            continue

    if not raw_dfs:
        logger.error("没有成功加载的数据")
        return False

    # 合并所有原始数据，再统一计算因子
    logger.info(f"\n合并 {len(raw_dfs)} 个批次的原始数据")
    all_raw_df = pl.concat(raw_dfs)
    logger.info(f"合并后共 {len(all_raw_df)} 行，开始计算因子")

    features_df = calculate_all_features(all_raw_df)

    # 输出 drop 前质量诊断，便于定位删行来源
    log_pre_drop_data_quality(features_df, logger)

    # 直接剔除预热样本（不做 fill 0）
    features_df = drop_warmup_samples(features_df, logger)
    features_df = drop_rows_with_feature_nulls(features_df, logger)
    log_pre_drop_data_quality(features_df, logger)
 
    rows_before = len(features_df)
    critical_columns = [
        col for col in (["timestamp", "date", "contract"] + ORDERBOOK_REQUIRED_COLUMNS)
        if col in features_df.columns
    ]
    final_df = features_df.drop_nulls(subset=critical_columns)
    rows_after = len(final_df)
    if rows_before > rows_after:
        logger.info(f"删除了 {rows_before - rows_after} 行关键字段为空的数据")

    # 保存最终结果
    output_path = get_output_filepath(
        start_date=start_date,
        end_date=end_date,
        timeframe=timeframe,
        symbol=symbol,
    )
    logger.info(f"保存最终结果到: {output_path}")

    if OUTPUT_FORMAT == "parquet":
        final_df.write_parquet(output_path)
    elif OUTPUT_FORMAT == "feather":
        final_df.write_ipc(output_path)
    else:
        final_df.write_csv(output_path)

    logger.info(f"成功保存 {len(final_df)} 行数据")
    return True


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='生成高频交易因子特征数据集')
    parser.add_argument('--start-date', type=str, default=START_DATE,
                        help=f'起始日期 (默认: {START_DATE})')
    parser.add_argument('--end-date', type=str, default=END_DATE,
                        help=f'结束日期 (默认: {END_DATE})')
    parser.add_argument('--strategy', type=str, default='single',
                        choices=['single'],
                        help='输出策略')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE_DAYS,
                        help=f'批处理大小（天数） (默认: {BATCH_SIZE_DAYS})')
    parser.add_argument('--timeframe', type=str, default=TIMEFRAME,
                        choices=['10s','20s','30s', '1m'],
                        help=f'时间粒度 (默认: {TIMEFRAME})')
    parser.add_argument('--commodity', type=str, default=COMMODITY,
                        help=f'品种名称 (默认: {COMMODITY})')
    parser.add_argument('--symbol', type=str, default=SYMBOL,
                        help=f'品种英文符号前缀 (默认: {SYMBOL})')
    parser.add_argument('--log-level', type=str, default=LOG_LEVEL,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help=f'日志级别 (默认: {LOG_LEVEL})')

    args = parser.parse_args()

    # 确保目录存在
    ensure_directories(symbol=args.symbol)

    # 配置日志
    setup_logging(LOG_FILE, args.log_level)
    logger = logging.getLogger(__name__)

    # 打印配置信息
    logger.info("="*80)
    logger.info("高频交易因子生成系统")
    logger.info("="*80)
    logger.info(f"起始日期: {args.start_date}")
    logger.info(f"结束日期: {args.end_date}")
    logger.info(f"品种: {args.commodity}")
    logger.info(f"品种符号: {args.symbol}")
    logger.info(f"时间粒度: {args.timeframe}")
    logger.info(f"输出策略: {args.strategy}")
    logger.info(f"批处理大小: {args.batch_size} 天")
    logger.info(f"输出格式: {OUTPUT_FORMAT}")
    logger.info(f"日志级别: {args.log_level}")
    logger.info(f"日志文件: {LOG_FILE}")
    logger.info("="*80)

    # 开始计时
    start_time = datetime.now()
    logger.info(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 根据策略执行
    try:
         
        success = generate_features_single_file(
            start_date=args.start_date,
            end_date=args.end_date,
            batch_size=args.batch_size,
            timeframe=args.timeframe,
            commodity=args.commodity,
            symbol=args.symbol,
        )
        if success:
            logger.info("\n单文件生成成功")
        else:
            logger.error("\n单文件生成失败")

    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}", exc_info=True)
        return 1

    # 结束计时
    end_time = datetime.now()
    elapsed = end_time - start_time

    logger.info("="*80)
    logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"总耗时: {elapsed}")
    logger.info("="*80)

    return 0


if __name__ == "__main__":
    exit(main())
