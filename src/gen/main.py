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
    OUTPUT_FORMAT,
    OUTPUT_STRATEGY,
    LOG_LEVEL,
    LOG_FILE,
    LOG_DIR,
    TIMEFRAME,
    ENABLE_DATA_VALIDATION,
    get_output_filepath,
    ensure_directories
)
from data_loader import (
    load_and_merge_date_range,
    validate_data,
    generate_date_range
)
from feature_calculator import calculate_all_features, get_feature_columns


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
) -> bool:
    """
    生成单个特征文件（分批处理后合并）

    Args:
        start_date: 起始日期
        end_date: 结束日期
        batch_size: 批处理大小（天数）
        timeframe: 时间粒度，如 '30s' 或 '1m'

    Returns:
        是否成功
    """
    logger = logging.getLogger(__name__)
    logger.info(f"使用单文件策略生成特征 (timeframe={timeframe})")

    # 生成日期范围
    all_dates = generate_date_range(start_date, end_date)
    total_days = len(all_dates)

    logger.info(f"总共需要处理 {total_days} 天，批大小 {batch_size} 天")

    # 分批处理
    batch_dfs = []
    for i in range(0, total_days, batch_size):
        batch_num = i // batch_size + 1
        total_batches = (total_days + batch_size - 1) // batch_size

        batch_start = all_dates[i]
        batch_end_idx = min(i + batch_size, total_days)
        batch_end = all_dates[batch_end_idx - 1]

        logger.info(f"\n处理批次 {batch_num}/{total_batches}: {batch_start} 至 {batch_end}")

        # 加载和处理数据
        try:
            # 使用新的加载和合并函数
            merged_df = load_and_merge_date_range(batch_start, batch_end, timeframe=timeframe)

            if merged_df is None:
                logger.warning(f"批次 {batch_num} 数据加载失败，跳过")
                continue

            features_df = calculate_all_features(merged_df)
          
           
            # 删除包含 nan 值的行（由周期性因子导致）
            rows_before = len(features_df)
            features_df = features_df.drop_nulls()
            rows_after = len(features_df)
            if rows_before > rows_after:
                logger.info(f"批次 {batch_num} 删除了 {rows_before - rows_after} 行包含 NaN 的数据")

            batch_dfs.append(features_df)

            logger.info(f"批次 {batch_num} 处理完成，{len(features_df)} 行")

        except Exception as e:
            logger.error(f"批次 {batch_num} 处理失败: {str(e)}\n{traceback.format_exc()}")
            continue

    # 合并所有批次
    if not batch_dfs:
        logger.error("没有成功处理的批次")
        return False

    logger.info(f"\n合并 {len(batch_dfs)} 个批次的数据")
    final_df = pl.concat(batch_dfs)

    # 保存最终结果
    output_path = get_output_filepath(start_date=start_date, end_date=end_date, timeframe=timeframe)
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
    parser.add_argument('--strategy', type=str, default=OUTPUT_STRATEGY,
                        choices=['single'],
                        help=f'输出策略 (默认: {OUTPUT_STRATEGY})')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE_DAYS,
                        help=f'批处理大小（天数） (默认: {BATCH_SIZE_DAYS})')
    parser.add_argument('--timeframe', type=str, default=TIMEFRAME,
                        choices=['10s','30s', '1m'],
                        help=f'时间粒度 (默认: {TIMEFRAME})')
    parser.add_argument('--log-level', type=str, default=LOG_LEVEL,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help=f'日志级别 (默认: {LOG_LEVEL})')

    args = parser.parse_args()

    # 确保目录存在
    ensure_directories()

    # 配置日志
    setup_logging(LOG_FILE, args.log_level)
    logger = logging.getLogger(__name__)

    # 打印配置信息
    logger.info("="*80)
    logger.info("高频交易因子生成系统")
    logger.info("="*80)
    logger.info(f"起始日期: {args.start_date}")
    logger.info(f"结束日期: {args.end_date}")
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
            args.start_date,
            args.end_date,
            args.batch_size,
            args.timeframe,
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