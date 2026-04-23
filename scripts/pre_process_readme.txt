1. reorganize_dce_data.py 解压文件组织目录
   python scripts/step1_reorganize_dce_data.py 燃料油
2. extract_main_contract_data.py  挑选主力合约文件
   python scripts/step2_extract_main_contract_data.py --commodity 燃料油
3. preprocess_volume_files.py 期货成交量统计合并分钟级别数据  （暂时没用，不执行）
   #python scripts/step3_preprocess_volume_files.py --commodity 燃料油
4 preprocess_order_files.py 5档委托合并分钟级别挂单数据    使用了v2，使用最后一笔快照
   python scripts/step4_preprocess_order_files_v2.py --commodity 燃料油 --interval 20s


5 生成因子
python src/gen/main.py --commodity 燃料油 --symbol fu --timeframe 20s --start-date 2023-01-01 --end-date 2026-04-01
python src/gen/main.py --commodity 燃料油 --symbol fu --timeframe 30s --start-date 2023-01-01 --end-date 2023-12-31

 
 
python src/gen/test_results.py 
python scripts/validate_factor_effectiveness.py --input output/split_20230101_20250101.feather --output-dir output/factor_validation --exact-dedup-threshold 0.9999
python src/gen/split_features.py --time-column timestamp -i output/features/features_20230101_20260401_30s.feather -r "20230101-20250101,20250101-20250701,20250701-20260301"
 
