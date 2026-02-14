# 测试指南

本文档介绍如何测试和验证高频交易因子生成系统。

## 测试流程概览

```
1. test_modules.py    → 测试各个模块功能（运行前）
2. quick_test.py      → 快速测试单天数据（运行前）
3. main.py            → 运行完整数据处理
4. test_results.py    → 验证输出结果（运行后）
```

---

## 1. 模块测试（必须）

**目的**: 在处理真实数据前，验证所有代码模块是否正常工作

**运行**:
```bash
cd src/gen
python test_modules.py
```

**测试内容**:
- ✓ 配置模块（路径、参数）
- ✓ 数据加载模块（读取、转换）
- ✓ 因子计算模块（所有因子）
- ✓ 集成测试（完整流程）

**预期输出**:
```
==================== 测试结果总结 ====================
配置模块: ✓ 通过
数据加载模块: ✓ 通过
因子计算模块: ✓ 通过
集成测试: ✓ 通过
====================================================
总计: 4/4 测试通过
所有测试通过！可以运行 main.py
```

**如果测试失败**:
- 检查 Python 版本 >= 3.8
- 确认已安装依赖: `pip install -r requirements.txt`
- 查看错误堆栈信息定位问题

---

## 2. 快速测试（推荐）

**目的**: 使用真实数据测试完整流程，但只处理一天的数据

**运行**:
```bash
# 使用默认日期（2023-06-30）
python quick_test.py

# 指定其他日期
python quick_test.py --date 2023-07-01
```

**测试流程**:
1. 加载单天订单簿和K线数据
2. 转换订单簿格式
3. 预处理K线数据
4. 合并数据
5. 计算所有因子
6. 保存测试结果到 `output/test_output.parquet`

**预期输出**:
```
============ 快速测试完成 ============
✓ 所有步骤执行成功
✓ 生成了 1440 行 × 62 列的特征数据
✓ 测试输出保存在: output/test_output.parquet

可以运行完整流程:
  python main.py
======================================
```

**检查点**:
- 订单簿数据应该有 ~14,400 行 (1440分钟 × 10档)
- K线数据应该有 ~1,440 行 (1440分钟)
- 最终特征数据应该有 ~1,440 行 × 62 列

**如果测试失败**:
- 检查数据文件是否存在:
  ```bash
  ls data/futures/um/daily/bookDepth/ETHUSDT/ETHUSDT-bookDepth-2023-06-30.zip
  ls data/futures/um/daily/klines/ETHUSDT/1m/ETHUSDT-1m-2023-06-30.zip
  ```
- 确认文件路径配置正确（查看 config.py）
- 查看详细错误信息

---

## 3. 运行完整流程

**前提**: test_modules.py 和 quick_test.py 都通过

**运行**:
```bash
# 使用默认配置（按月输出）
python main.py

# 指定日期范围
python main.py --start-date 2023-01-01 --end-date 2023-12-31

# 单文件输出
python main.py --strategy single --batch-size 30

# 设置日志级别
python main.py --log-level DEBUG
```

**监控进度**:
```bash
# 实时查看日志
tail -f logs/feature_generation_*.log

# 查看输出文件
ls -lh output/features/
```

---

## 4. 结果验证（必须）

**目的**: 验证生成的特征数据质量

**运行**:
```bash
# 验证单个文件
python test_results.py --file output/features/features_202306.parquet

# 验证所有文件
python test_results.py --all

# 验证测试输出
python test_results.py --file output/test_output.parquet
```

**验证内容**:

### 4.1 基本信息
- 数据行数
- 数据列数
- 文件大小

### 4.2 列完整性
- 所有必需列是否存在
- 62个因子是否完整

### 4.3 空值检查
- 统计空值数量
- 标识有空值的列
- 对数收益率第一行空值是正常的

### 4.4 数据范围检查
- ✓ `bid1_price < ask1_price`
- ✓ `volume_imbalance ∈ [-1, 1]`
- ✓ 所有价格 > 0
- ✓ 无无穷值 (inf)

### 4.5 统计信息
- 关键因子的均值、标准差
- 数据分布情况

### 4.6 时间连续性
- 时间戳范围
- 缺失的时间点

**预期输出**:
```
==================== 验证结果 ====================
1. 基本信息
   - 数据行数: 43,200
   - 数据列数: 62
   - 文件大小: 12.34 MB

2. 必需列检查: ✓ 通过

3. 因子列检查: ✓ 通过
   - 预期: 37 个
   - 实际: 37 个

4. 空值检查
   - 总空值数: 6
   - 有空值的列: 6 个 (log_return_* 第一行)

5. 数据范围检查: ✓ 通过

=================================================
验证结果: ✓ 全部通过
=================================================
```

**验证报告**:
- 自动保存到 `*_validation_report.txt`
- 包含详细的统计信息和问题列表

---

## 常见问题排查

### Q1: test_modules.py 失败

**症状**: 导入错误或模块找不到

**解决**:
```bash
# 确认在正确目录
cd /home/lanceliang/opt/aiwork/MacroHFT_Features/src/gen

# 检查依赖
pip install -r requirements.txt

# 检查 Python 版本
python --version  # 应该 >= 3.8
```

### Q2: quick_test.py 找不到数据文件

**症状**: "无法加载订单簿数据" 或 "无法加载K线数据"

**解决**:
```bash
# 1. 检查文件是否存在
ls data/futures/um/daily/bookDepth/ETHUSDT/
ls data/futures/um/daily/klines/ETHUSDT/1m/

# 2. 检查文件命名
# 应该是: ETHUSDT-bookDepth-2023-06-30.zip
# 应该是: ETHUSDT-1m-2023-06-30.zip

# 3. 查看配置
python -c "from config import get_bookdepth_filepath; print(get_bookdepth_filepath('2023-06-30'))"
```

### Q3: main.py 内存不足

**症状**: "MemoryError" 或进程被杀死

**解决**:
```bash
# 减小批处理大小
python main.py --batch-size 10

# 使用按月策略（更省内存）
python main.py --strategy monthly
```

### Q4: test_results.py 发现数据问题

**症状**: 验证报告显示多个问题

**解决**:
1. 查看详细报告: `cat output/features/*_validation_report.txt`
2. 检查原始数据质量
3. 查看 main.py 的日志文件
4. 如果是已知问题（如第一行log_return为空），可以忽略

### Q5: 因子值异常

**症状**: 因子值为 NaN、Inf 或超出合理范围

**解决**:
```bash
# 检查原始数据
python quick_test.py --date <问题日期>

# 查看详细统计
python test_results.py --file <问题文件>

# 检查除零保护（feature_calculator.py）
```

---

## 测试检查清单

运行 main.py 之前:
- [ ] `test_modules.py` 全部通过
- [ ] `quick_test.py` 成功运行
- [ ] 测试输出文件无异常
- [ ] 确认数据文件路径正确

运行 main.py 之后:
- [ ] 输出文件已生成
- [ ] `test_results.py` 验证通过
- [ ] 验证报告无严重问题
- [ ] 数据行数、列数符合预期
- [ ] 关键因子统计合理

---

## 性能基准

**单天数据** (quick_test.py):
- 处理时间: < 10秒
- 内存占用: < 500MB
- 输出大小: ~0.5MB

**单月数据** (main.py, monthly):
- 处理时间: ~5分钟
- 内存占用: ~2GB
- 输出大小: ~15MB

**全量数据** (3年):
- 处理时间: ~3-5小时
- 内存占用: ~4-8GB (取决于batch_size)
- 输出大小: ~500MB

---

## 下一步

测试全部通过后，可以:

1. **处理完整数据集**
   ```bash
   python main.py --start-date 2023-01-01 --end-date 2026-01-01
   ```

2. **使用生成的特征**
   ```python
   import polars as pl
   df = pl.read_parquet("output/features/features_202306.parquet")
   ```

3. **进行机器学习建模**
   - 特征已经标准化和归一化
   - 可以直接用于模型训练

---

## 获取帮助

- 查看详细文档: [README.md](README.md)
- 查看需求文档: [../../docs/freatures_process.md](../../docs/freatures_process.md)
- 查看因子说明: [../../docs/factor-desc.md](../../docs/factor-desc.md)
