"""
主执行脚本
生成高频交易因子特征数据集
"""

import polars as pl
import logging
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
    ENABLE_DATA_VALIDATION,
    get_output_filepath,
    ensure_directories
)
from data_loader import (
    load_date_range_data,
    pivot_bookdepth,
    preprocess_kline,
    merge_data,
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


def process_batch(
    start_date: str,
    end_date: str,
    output_path: Path
) -> bool:
    """
    处理一批数据（日期范围内）

    Args:
        start_date: 起始日期
        end_date: 结束日期
        output_path: 输出文件路径

    Returns:
        是否成功
    """
    logger = logging.getLogger(__name__)

    logger.info("="*80)
    logger.info(f"处理批次: {start_date} 至 {end_date}")
    logger.info("="*80)

    try:
        # 1. 加载数据
        logger.info("步骤 1/5: 加载原始数据")
        bookdepth_df, kline_df = load_date_range_data(start_date, end_date)

        if bookdepth_df is None or kline_df is None:
            logger.error("数据加载失败")
            return False

        # 2. 转换订单簿格式
        logger.info("步骤 2/5: 转换订单簿格式")
        bookdepth_wide = pivot_bookdepth(bookdepth_df)

        # 3. 预处理K线数据
        logger.info("步骤 3/5: 预处理K线数据")
        kline_processed = preprocess_kline(kline_df)

        # 4. 合并数据
        logger.info("步骤 4/5: 合并订单簿和K线数据")
        merged_df = merge_data(bookdepth_wide, kline_processed)

        # 数据验证
        if ENABLE_DATA_VALIDATION:
            logger.info("执行数据质量验证")
            if not validate_data(merged_df):
                logger.warning("数据验证未通过，但继续处理")

        # 5. 计算因子
        logger.info("步骤 5/5: 计算所有因子")
        features_df = calculate_all_features(merged_df)

        # 删除包含 nan 值的行（由周期性因子导致）
        rows_before = len(features_df)
        features_df = features_df.drop_nulls()
        rows_after = len(features_df)
        if rows_before > rows_after:
            logger.info(f"删除了 {rows_before - rows_after} 行包含 NaN 的数据")

        # 6. 保存结果
        logger.info(f"保存结果到: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if OUTPUT_FORMAT == "parquet":
            features_df.write_parquet(output_path)
        elif OUTPUT_FORMAT == "feather":
            features_df.write_ipc(output_path)
        else:
            features_df.write_csv(output_path)

        logger.info(f"成功保存 {len(features_df)} 行数据")
        logger.info("="*80)

        return True

    except Exception as e:
        logger.error(f"处理批次时发生错误: {str(e)}", exc_info=True)
        return False


def generate_features_by_month(
    start_date: str,
    end_date: str
) -> int:
    """
    按月生成特征数据

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'

    Returns:
        成功处理的月份数
    """
    logger = logging.getLogger(__name__)
    logger.info("使用按月策略生成特征")

    # 解析日期
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # 生成月份列表
    months = []
    current = start.replace(day=1)  # 月初
    while current < end:
        next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        months.append((
            current.strftime("%Y-%m-%d"),
            min(next_month, end).strftime("%Y-%m-%d"),
            current.strftime("%Y%m")
        ))
        current = next_month

    logger.info(f"总共需要处理 {len(months)} 个月")

    # 处理每个月
    success_count = 0
    for i, (month_start, month_end, month_str) in enumerate(months, 1):
        logger.info(f"\n处理月份 {i}/{len(months)}: {month_str}")

        output_path = get_output_filepath(month_str=month_str)

        # 检查文件是否已存在
        if output_path.exists():
            logger.warning(f"输出文件已存在: {output_path}")
            response = input("是否覆盖？(y/n): ")
            if response.lower() != 'y':
                logger.info("跳过此月份")
                continue

        # 处理批次
        if process_batch(month_start, month_end, output_path):
            success_count += 1
        else:
            logger.error(f"处理月份 {month_str} 失败")

    return success_count


def generate_features_single_file(
    start_date: str,
    end_date: str,
    batch_size: int = BATCH_SIZE_DAYS
) -> bool:
    """
    生成单个特征文件（分批处理后合并）

    Args:
        start_date: 起始日期
        end_date: 结束日期
        batch_size: 批处理大小（天数）

    Returns:
        是否成功
    """
    logger = logging.getLogger(__name__)
    logger.info("使用单文件策略生成特征")

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
            bookdepth_df, kline_df = load_date_range_data(batch_start, batch_end)

            if bookdepth_df is None or kline_df is None:
                logger.warning(f"批次 {batch_num} 数据加载失败，跳过")
                continue

            bookdepth_wide = pivot_bookdepth(bookdepth_df)
            kline_processed = preprocess_kline(kline_df)
            merged_df = merge_data(bookdepth_wide, kline_processed)
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
            logger.error(f"批次 {batch_num} 处理失败: {str(e)}")
            continue

    # 合并所有批次
    if not batch_dfs:
        logger.error("没有成功处理的批次")
        return False

    logger.info(f"\n合并 {len(batch_dfs)} 个批次的数据")
    final_df = pl.concat(batch_dfs)

    # 保存最终结果
    output_path = get_output_filepath(start_date=start_date, end_date=end_date)
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
                        choices=['single', 'monthly'],
                        help=f'输出策略 (默认: {OUTPUT_STRATEGY})')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE_DAYS,
                        help=f'批处理大小（天数） (默认: {BATCH_SIZE_DAYS})')
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
        if args.strategy == "monthly":
            success_count = generate_features_by_month(args.start_date, args.end_date)
            logger.info(f"\n成功处理 {success_count} 个月的数据")
        else:
            success = generate_features_single_file(
                args.start_date,
                args.end_date,
                args.batch_size
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
