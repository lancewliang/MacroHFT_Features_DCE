1. reorganize_dce_data.py 解压文件组织目录
2. extract_main_contract_data.py  挑选主力合约文件
3. preprocess_volume_files.py 期货成交量统计合并分钟级别数据  （暂时没用）
4 preprocess_order_files.py 5档委托合并分钟级别挂单数据    使用了v2，使用最后一笔快照




 
python main.py --start-date 2023-01-01 --end-date 2026-01-01 --timeframe 1m
python test_results.py 
python src/gen/split_features.py --time-column timestamp -i output/features/features_20230101_20251231.feather -r "20230101-20250201,20250201-20250701,20250701-20260101"