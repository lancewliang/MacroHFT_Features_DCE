"""
快速测试脚本
使用单天真实数据测试完整流程
"""

import polars as pl
import logging
from pathlib import Path
import sys

from config import ensure_directories
from data_loader import (
    load_daily_bookdepth,
    load_daily_kline,
    pivot_bookdepth,
    preprocess_kline,
    merge_data,
    validate_data
)
from feature_calculator import calculate_all_features, get_feature_columns


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def quick_test(test_date: str = "2023-06-30"):
    """
    快速测试单天数据处理流程

    Args:
        test_date: 测试日期
    """
    logger.info("="*80)
    logger.info(f"快速测试：处理 {test_date} 的数据")
    logger.info("="*80)

    try:
        # 1. 加载数据
        logger.info("\n步骤 1/5: 加载原始数据")
        logger.info("-"*60)

        bookdepth_df = load_daily_bookdepth(test_date)
        if bookdepth_df is None:
            logger.error(f"❌ 无法加载订单簿数据: {test_date}")
            logger.error("请检查:")
            logger.error("  1. 数据文件是否存在")
            logger.error("  2. 文件路径是否正确（参考 config.py）")
            return False

        kline_df = load_daily_kline(test_date)
        if kline_df is None:
            logger.error(f"❌ 无法加载K线数据: {test_date}")
            logger.error("请检查:")
            logger.error("  1. 数据文件是否存在")
            logger.error("  2. 文件路径是否正确（参考 config.py）")
            return False

        logger.info(f"✓ 订单簿数据: {bookdepth_df.shape[0]} 行 × {bookdepth_df.shape[1]} 列")
        logger.info(f"✓ K线数据: {kline_df.shape[0]} 行 × {kline_df.shape[1]} 列")

        # 2. 转换订单簿格式
        logger.info("\n步骤 2/5: 转换订单簿格式（长格式 → 宽格式）")
        logger.info("-"*60)

        bookdepth_wide = pivot_bookdepth(bookdepth_df)
        logger.info(f"✓ 转换后: {bookdepth_wide.shape[0]} 行 × {bookdepth_wide.shape[1]} 列")

        # 显示前几列
        sample_cols = bookdepth_wide.columns[:5]
        logger.info(f"  列示例: {sample_cols}")

        # 3. 预处理K线数据
        logger.info("\n步骤 3/5: 预处理K线数据")
        logger.info("-"*60)

        kline_processed = preprocess_kline(kline_df)
        logger.info(f"✓ 预处理后: {kline_processed.shape[0]} 行 × {kline_processed.shape[1]} 列")
        logger.info(f"  列名: {kline_processed.columns}")

        # 4. 合并数据
        logger.info("\n步骤 4/5: 合并订单簿和K线数据")
        logger.info("-"*60)

        merged_df = merge_data(bookdepth_wide, kline_processed)
        logger.info(f"✓ 合并后: {merged_df.shape[0]} 行 × {merged_df.shape[1]} 列")

        # 数据验证
        logger.info("\n  数据质量验证:")
        if validate_data(merged_df):
            logger.info("  ✓ 数据质量检查通过")
        else:
            logger.warning("  ⚠ 数据质量检查发现问题（但继续处理）")

        # 5. 计算因子
        logger.info("\n步骤 5/5: 计算所有因子")
        logger.info("-"*60)

        features_df = calculate_all_features(merged_df)
        logger.info(f"✓ 最终数据: {features_df.shape[0]} 行 × {features_df.shape[1]} 列")

        # 验证因子完整性
        expected_features = get_feature_columns()
        existing_features = [col for col in expected_features if col in features_df.columns]
        missing_features = [col for col in expected_features if col not in features_df.columns]

        logger.info(f"\n因子统计:")
        logger.info(f"  预期因子数: {len(expected_features)}")
        logger.info(f"  实际因子数: {len(existing_features)}")

        if missing_features:
            logger.warning(f"  缺失因子: {len(missing_features)} 个")
            for feat in missing_features:
                logger.warning(f"    - {feat}")
        else:
            logger.info(f"  ✓ 所有因子都已生成")

        # 显示数据预览
        logger.info("\n数据预览（前3行）:")
        logger.info("-"*60)
        print(features_df.head(3))

        # 显示关键因子统计
        logger.info("\n关键因子统计:")
        logger.info("-"*60)
        key_features = ['volume_imbalance', 'price_spread', 'wap_1', 'kmid', 'klen']
        for feat in key_features:
            if feat in features_df.columns:
                mean_val = features_df[feat].mean()
                std_val = features_df[feat].std()
                min_val = features_df[feat].min()
                max_val = features_df[feat].max()
                logger.info(f"{feat}:")
                logger.info(f"  均值={mean_val:.6f}, 标准差={std_val:.6f}")
                logger.info(f"  范围=[{min_val:.6f}, {max_val:.6f}]")

        # 打印所有因子名字
        logger.info("\n所有因子列表:")
        logger.info("-"*60)
        feature_columns = [col for col in features_df.columns if col not in ['time', 'timestamp']]
        for i, feat in enumerate(feature_columns, 1):
            logger.info(f"  {i:2d}. {feat}")
        logger.info(f"\n总计: {len(feature_columns)} 个因子")

        # 保存测试结果
        ensure_directories()
        from config import OUTPUT_FORMAT

        # 根据配置的格式保存文件
        if OUTPUT_FORMAT == "feather":
            output_path = Path("output/features/test_output.feather")
        elif OUTPUT_FORMAT == "parquet":
            output_path = Path("output/features/test_output.parquet")
        else:
            output_path = Path("output/features/test_output.csv")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n保存测试结果到: {output_path}")
        if OUTPUT_FORMAT == "parquet":
            features_df.write_parquet(output_path)
        elif OUTPUT_FORMAT == "feather":
            features_df.write_ipc(output_path)
        else:
            features_df.write_csv(output_path)

        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ 文件已保存 ({file_size:.2f} MB)")

        # 测试总结
        logger.info("\n" + "="*80)
        logger.info("快速测试完成")
        logger.info("="*80)
        logger.info("✓ 所有步骤执行成功")
        logger.info(f"✓ 生成了 {features_df.shape[0]} 行 × {features_df.shape[1]} 列的特征数据")
        logger.info(f"✓ 测试输出保存在: {output_path}")
        logger.info("\n可以运行完整流程:")
        logger.info("  python main.py")
        logger.info("="*80)

        return True

    except Exception as e:
        logger.error(f"\n❌ 快速测试失败: {str(e)}", exc_info=True)
        logger.error("\n故障排查建议:")
        logger.error("  1. 运行 python test_modules.py 检查模块")
        logger.error("  2. 检查数据文件路径是否正确")
        logger.error("  3. 查看完整错误堆栈信息")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='快速测试单天数据处理')
    parser.add_argument('--date', type=str, default='2023-06-30',
                        help='测试日期 (格式: YYYY-MM-DD)')

    args = parser.parse_args()

    # 运行快速测试
    success = quick_test(args.date)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
