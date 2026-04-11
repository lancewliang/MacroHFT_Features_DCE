1. reorganize_dce_data.py 解压文件组织目录
2. extract_main_contract_data.py  挑选主力合约文件
3. preprocess_volume_files.py 期货成交量统计合并分钟级别数据  （暂时没用，不执行）
4 preprocess_order_files.py 5档委托合并分钟级别挂单数据    使用了v2，使用最后一笔快照




 
python src/gen/main.py --start-date 2023-01-01 --end-date 2026-04-01 --timeframe 30s
python src/gen/test_results.py 
python scripts/validate_factor_effectiveness.py --input output/split_20230101_20250101.feather --output-dir output/factor_validation --exact-dedup-threshold 0.9999
python src/gen/split_features.py --time-column timestamp -i output/features/features_20230101_20260401_30s.feather -r "20230101-20250101,20250101-20250701,20250701-20260301"


新增：抗分布漂移因子层（2026-04）
1) 相对化因子（窗口 20/60/180/360）
- 价格标准化：close_price/wap_1/wap_2/bid1_price/ask1_price/price_spread 的 rolling z-score
  命名: {column}_zscore_{window}
- 量能与价格比值：close_price/wap_1/volume/trade_volume_delta/turnover_delta/open_interest/klen 的 rolling ratio
  命名: {column}_ratio_{window}

2) 市场状态（regime）因子
- 波动状态比值：vol_regime_ratio_20_60, vol_regime_ratio_60_180, vol_regime_ratio_60_360
- 活跃度状态比值：volume_regime_ratio_60_360, turnover_regime_ratio_60_360
- 流动性状态比值：spread_regime_ratio_60_360
- 盘口近端深度状态：depth_near_share, depth_near_share_zscore_60, depth_near_share_zscore_360

目的：
- 降低绝对价格抬升导致的因子漂移，提升跨阶段（val -> test）稳健性

验证脚本新增输出：
- exact_corr_dedup_h{horizon}.csv：近乎完全重复特征去重明细（按该 horizon 的 |IC| 选保留）
- feature_pool_after_exact_dedup_h{horizon}.txt：去重后的候选池
- final_feature_list_short/mid/long.txt：策略别名最终特征清单（可直接用于训练）
