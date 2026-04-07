# 高频交易因子描述文档

本文档按当前代码实现和 [`target_factor.md`](./target_factor.md) 说明 SH 因子口径。

## 一、基础输入字段

### 1. 五档价格字段

- **ask1_price ~ ask5_price**: 卖方五档价格
  - 含义：卖一到卖五的盘口价格
  - 来源：上游五档行情快照字段
  - 用途：反映卖方报价结构，`ask1_price` 为最优卖价

- **bid1_price ~ bid5_price**: 买方五档价格
  - 含义：买一到买五的盘口价格
  - 来源：上游五档行情快照字段
  - 用途：反映买方报价结构，`bid1_price` 为最优买价

### 2. 五档数量字段

- **ask1_size ~ ask5_size**: 卖方五档挂单量
  - 含义：对应卖方各价格档位上的挂单深度
  - 用途：反映卖方各档位的订单分布

- **bid1_size ~ bid5_size**: 买方五档挂单量
  - 含义：对应买方各价格档位上的挂单深度
  - 用途：反映买方各档位的订单分布

### 3. K线价格字段

- **open_price**: 窗口开盘价
- **high_price**: 窗口最高价
- **low_price**: 窗口最低价
- **close_price**: 窗口收盘价

### 4. 成交与持仓快照字段

- **total_trade_volume**: 累计成交量快照
  - 含义：截至当前快照时点的累计成交量
  - 说明：不是当前窗口内新增成交量

- **turnover**: 累计成交额快照
  - 含义：截至当前快照时点的累计成交额
  - 说明：不是当前窗口内新增成交额

- **open_interest**: 持仓量快照
  - 含义：当前快照时点的持仓量
  - 说明：可直接使用水平值，也可转成相邻快照变化量

---

## 二、K线相关因子（Candlestick Features）

### 1. 中间变量

- **max_oc**: `max(open_price, close_price)`
  - 含义：K线实体上沿
  - 说明：仅作为中间变量使用，不属于最终输出因子

- **min_oc**: `min(open_price, close_price)`
  - 含义：K线实体下沿
  - 说明：仅作为中间变量使用，不属于最终输出因子

### 2. K线实体特征

- **kmid**: K线实体方向
  - 计算：`close_price - open_price`
  - 含义：收盘价与开盘价之差
  - 用途：正值通常表示上涨，负值通常表示下跌

- **kmid2**: K线实体归一化比率
  - 计算：`(close_price - open_price) / (high_price - low_price)`
  - 含义：实体长度占整根K线振幅的比例
  - 用途：衡量实体相对强度

### 3. K线振幅特征

- **klen**: K线总长度
  - 计算：`high_price - low_price`
  - 含义：当前窗口价格振幅
  - 用途：反映波动幅度

### 4. 上下影线特征

- **kup**: 上影线长度
  - 计算：`high_price - max_oc`
  - 含义：最高价到实体上沿的距离
  - 用途：反映上方压力

- **kup2**: 上影线归一化比率
  - 计算：`(high_price - max_oc) / (high_price - low_price)`
  - 含义：上影线占总振幅的比例
  - 用途：反映归一化后的上方压力

- **klow**: 下影线长度
  - 计算：`min_oc - low_price`
  - 含义：实体下沿到最低价的距离
  - 用途：反映下方支撑

- **klow2**: 下影线归一化比率
  - 计算：`(min_oc - low_price) / (high_price - low_price)`
  - 含义：下影线占总振幅的比例
  - 用途：反映归一化后的下方支撑

### 5. K线位置特征

- **ksft**: K线偏移量
  - 计算：`2 * close_price - high_price - low_price`
  - 含义：收盘价相对高低点中枢的位置偏移
  - 用途：衡量收盘更接近高点还是低点

- **ksft2**: K线偏移归一化比率
  - 计算：`ksft / (high_price - low_price)`
  - 含义：归一化后的 K 线位置偏移
  - 用途：便于跨时段比较

说明：

- 当前实现中，当 `high_price == low_price` 时，`kmid2`、`kup2`、`klow2`、`ksft2` 返回 `0`。

---

## 三、订单簿归一化因子（Normalized Size Features）

### 1. 总订单量

- **volume**: 五档总挂单量
  - 计算：`Σ(bid_i_size) + Σ(ask_i_size)`，`i = 1..5`
  - 含义：当前时刻订单簿前五档总深度
  - 用途：衡量盘口流动性

### 2. 归一化订单量

- **bid1_size_n ~ bid5_size_n**: 买方归一化挂单量
  - 计算：`bid_i_size / volume`
  - 含义：各买方档位挂单量占总盘口量的比例
  - 用途：反映买盘深度分布

- **ask1_size_n ~ ask5_size_n**: 卖方归一化挂单量
  - 计算：`ask_i_size / volume`
  - 含义：各卖方档位挂单量占总盘口量的比例
  - 用途：反映卖盘深度分布

---

## 四、加权平均价格因子（WAP Features）

### 1. 档位加权均价

- **wap_1**: 第一档加权均价
  - 计算：`(ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)`
  - 含义：基于买一卖一数量加权的均衡价格
  - 用途：刻画最优档位的局部均衡价

- **wap_2**: 第二档加权均价
  - 计算：`(ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)`
  - 含义：基于买二卖二数量加权的均衡价格
  - 用途：刻画次优档位的局部均衡价

### 2. 档位平衡差异

- **wap_balance**: 档位加权均价差异
  - 计算：`abs(wap_1 - wap_2)`
  - 含义：第一档和第二档均衡价格的绝对差
  - 用途：反映不同档位之间的结构一致性

---

## 五、价差因子（Spread Features）

### 1. 单边价差

- **buy_spread**: 买盘价差
  - 计算：`abs(bid1_price - bid5_price)`
  - 含义：买一到买五的价格跨度
  - 用途：反映买盘价格分布宽度

- **sell_spread**: 卖盘价差
  - 计算：`abs(ask1_price - ask5_price)`
  - 含义：卖一到卖五的价格跨度
  - 用途：反映卖盘价格分布宽度

### 2. 买卖价差

- **price_spread**: 归一化买卖价差
  - 计算：`2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)`
  - 含义：买一卖一价差的归一化表达
  - 用途：反映流动性与交易成本

---

## 六、量能因子（Volume Features）

### 1. 单边总量

- **buy_volume**: 买方五档总量
  - 计算：`bid1_size + bid2_size + bid3_size + bid4_size + bid5_size`
  - 含义：买方前五档挂单量之和
  - 用途：衡量买盘整体深度

- **sell_volume**: 卖方五档总量
  - 计算：`ask1_size + ask2_size + ask3_size + ask4_size + ask5_size`
  - 含义：卖方前五档挂单量之和
  - 用途：衡量卖盘整体深度

### 2. 买卖不平衡

- **volume_imbalance**: 买卖量不平衡度
  - 计算：`(buy_volume - sell_volume) / (buy_volume + sell_volume)`
  - 含义：买盘与卖盘总量的相对差异
  - 用途：衡量盘口力量偏向

---

## 七、VWAP 因子（VWAP Features）

- **sell_vwap**: 卖方加权均价
  - 计算：`Σ(ask_i_size_n * ask_i_price)`，`i = 1..5`
  - 含义：卖方五档价格按归一化数量加权后的平均水平
  - 用途：反映卖盘整体价格中枢

- **buy_vwap**: 买方加权均价
  - 计算：`Σ(bid_i_size_n * bid_i_price)`，`i = 1..5`
  - 含义：买方五档价格按归一化数量加权后的平均水平
  - 用途：反映买盘整体价格中枢

---

## 八、对数收益率因子（Log Return Features）

### 1. 盘口价格对数收益率

- **log_return_bid1_price**: 买一价对数收益率
  - 计算：`log(bid1_price[t] / bid1_price[t-1])`
  - 含义：买一价格的对数变化率
  - 用途：衡量最优买价变动速度

- **log_return_bid2_price**: 买二价对数收益率
  - 计算：`log(bid2_price[t] / bid2_price[t-1])`
  - 含义：买二价格的对数变化率
  - 用途：衡量次优买价变动速度

- **log_return_ask1_price**: 卖一价对数收益率
  - 计算：`log(ask1_price[t] / ask1_price[t-1])`
  - 含义：卖一价格的对数变化率
  - 用途：衡量最优卖价变动速度

- **log_return_ask2_price**: 卖二价对数收益率
  - 计算：`log(ask2_price[t] / ask2_price[t-1])`
  - 含义：卖二价格的对数变化率
  - 用途：衡量次优卖价变动速度

### 2. WAP 对数收益率

- **log_return_wap_1**: 第一档 WAP 对数收益率
  - 计算：`log(wap_1[t] / wap_1[t-1])`
  - 含义：第一档均衡价格的对数变化率
  - 用途：衡量最优档位均衡价的变动趋势

- **log_return_wap_2**: 第二档 WAP 对数收益率
  - 计算：`log(wap_2[t] / wap_2[t-1])`
  - 含义：第二档均衡价格的对数变化率
  - 用途：衡量次优档位均衡价的变动趋势

说明：

- `log_return_*` 基于价格序列，不基于 `*_size_n`。
- 第一行通常为空，因为不存在 `t-1`。

---

## 八点五、成交与持仓快照衍生因子（Trade Snapshot Features）

说明：

- `total_trade_volume`、`turnover`、`open_interest` 都按快照字段处理。
- 成交相关因子先做相邻快照差分，再计算滚动波动率和滚动斜率。
- 差分默认按同一 `date / contract` 分组，避免跨日累计值串联。

### 1. 快照差分因子

- **trade_volume_delta**: 成交量快照差分
  - 计算：`max(total_trade_volume[t] - total_trade_volume[t-1], 0)`
  - 含义：相邻快照间新增成交量
  - 用途：刻画该快照区间内的真实成交活跃度

- **turnover_delta**: 成交额快照差分
  - 计算：`max(turnover[t] - turnover[t-1], 0)`
  - 含义：相邻快照间新增成交额
  - 用途：刻画该快照区间内的真实成交金额变化

- **open_interest_change**: 持仓量变化
  - 计算：`open_interest[t] - open_interest[t-1]`
  - 含义：相邻快照间持仓量净变化
  - 用途：区分增仓、减仓与换手型成交

- **open_interest_change_ratio**: 持仓量变化率
  - 计算：`open_interest_change / abs(open_interest[t-1])`
  - 含义：相对上一时点持仓量的变化比例
  - 用途：便于跨时段比较持仓变化强弱

- **open_interest_change_per_trade**: 单位成交对应的持仓变化
  - 计算：`open_interest_change / trade_volume_delta`
  - 含义：每单位新增成交量对应的净增仓或减仓强度
  - 用途：区分增仓推进、减仓回补与单纯换手

### 2. 成交价格衍生因子

- **avg_trade_price**: 快照区间成交均价
  - 计算：当 `trade_volume_delta > 0` 时，`turnover_delta / trade_volume_delta`；否则回退到 `close_price`
  - 含义：相邻两次快照之间成交的平均价格
  - 用途：刻画成交重心相对盘口中枢的位置

- **avg_trade_price_bias**: 成交均价偏离
  - 计算：`(avg_trade_price - wap_1) / wap_1`
  - 含义：快照区间成交均价相对一档 WAP 的归一化偏离
  - 用途：衡量成交是否偏向主动吃单或被动成交

- **avg_trade_price_bias_change**: 成交均价偏离变化率
  - 计算：`avg_trade_price_bias[t] - avg_trade_price_bias[t-1]`
  - 含义：相邻快照间成交方向偏离的变化幅度
  - 用途：识别成交从偏买侧快速切向偏卖侧，或反之

### 3. 滚动波动率与窗口斜率

- **trade_volume_delta_vol_60 / 180 / 360**: 新增成交量滚动波动率
  - 计算：`RollingStd(trade_volume_delta, w)`

- **turnover_delta_vol_60 / 180 / 360**: 新增成交额滚动波动率
  - 计算：`RollingStd(turnover_delta, w)`

- **avg_trade_price_bias_vol_60 / 180 / 360**: 成交均价偏离滚动波动率
  - 计算：`RollingStd(avg_trade_price_bias, w)`

- **open_interest_change_vol_60 / 180 / 360**: 持仓变化滚动波动率
  - 计算：`RollingStd(open_interest_change, w)`

- **trade_volume_delta_zscore_60 / 180 / 360**: 新增成交量滚动标准化
  - 计算：`(trade_volume_delta - RollingMean(trade_volume_delta, w)) / RollingStd(trade_volume_delta, w)`
  - 含义：当前新增成交量相对过去窗口分布的偏离程度
  - 用途：识别异常放量快照

- **turnover_delta_zscore_60 / 180 / 360**: 新增成交额滚动标准化
  - 计算：`(turnover_delta - RollingMean(turnover_delta, w)) / RollingStd(turnover_delta, w)`
  - 含义：当前新增成交额相对过去窗口分布的偏离程度
  - 用途：识别异常大额成交快照

- **open_interest_change_zscore_60 / 180 / 360**: 持仓变化滚动标准化
  - 计算：`(open_interest_change - RollingMean(open_interest_change, w)) / RollingStd(open_interest_change, w)`
  - 含义：当前持仓变化相对过去窗口分布的偏离程度
  - 用途：识别异常增仓或减仓

- **avg_trade_price_bias_zscore_60 / 180 / 360**: 成交均价偏离滚动标准化
  - 计算：`(avg_trade_price_bias - RollingMean(avg_trade_price_bias, w)) / RollingStd(avg_trade_price_bias, w)`
  - 含义：当前成交均价偏离相对过去窗口分布的偏离程度
  - 用途：识别异常强的主动成交方向偏移

- **signed_trade_pressure_60 / 180 / 360**: 方向化成交压力
  - 计算：`sign(avg_trade_price_bias) * trade_volume_delta_zscore_w`
  - 含义：用成交均价相对盘口中枢的方向，对异常成交量做方向化
  - 用途：识别偏买侧或偏卖侧的异常放量

- **signed_open_interest_pressure_60 / 180 / 360**: 方向化持仓压力
  - 计算：`sign(avg_trade_price_bias) * open_interest_change_zscore_w`
  - 含义：用成交方向对异常持仓变化做方向化
  - 用途：识别主动成交伴随的异常增仓或减仓

- **trade_ofi_resonance_60 / 180 / 360**: 成交偏离与 OFI 共振
  - 计算：`avg_trade_price_bias_zscore_w * ofi_zscore_w`
  - 含义：异常成交方向偏离与异常订单流冲击的乘积
  - 用途：识别成交方向和盘口订单流同向增强的强共振时刻

- **trade_volume_delta_slope_60 / 180 / 360**: 新增成交量窗口斜率
  - 计算：`(trade_volume_delta[t] - trade_volume_delta[t-w]) / w`

- **turnover_delta_slope_60 / 180 / 360**: 新增成交额窗口斜率
  - 计算：`(turnover_delta[t] - turnover_delta[t-w]) / w`

- **avg_trade_price_bias_slope_60 / 180 / 360**: 成交均价偏离窗口斜率
  - 计算：`(avg_trade_price_bias[t] - avg_trade_price_bias[t-w]) / w`

- **open_interest_slope_60 / 180 / 360**: 持仓量水平窗口斜率
  - 计算：`(open_interest[t] - open_interest[t-w]) / w`

说明：

- 当前统一生成 `60 / 180 / 360` 三档窗口。
- 对应滚动因子在前 `w` 行可能为空，因为滚动窗口不足。

---

## 九、稳定性因子（Stability Features）

### 1. 最优价差持续时长

- **best_spread_duration**: best spread 持续时长
  - 计算：若 `price_spread[t] == price_spread[t-1]`，则 `best_spread_duration[t] = best_spread_duration[t-1] + 1`，否则为 `1`
  - 含义：买一卖一价差连续未变化的快照数
  - 用途：衡量最优价差的稳定性与盘口黏性

### 2. 最优报价持续时长

- **best_quote_duration**: best quote 未变化持续时长
  - 计算：若 `bid1_price[t] == bid1_price[t-1]` 且 `ask1_price[t] == ask1_price[t-1]`，则 `best_quote_duration[t] = best_quote_duration[t-1] + 1`，否则为 `1`
  - 含义：买一卖一价格对连续未变化的快照数
  - 用途：衡量最优报价的稳定性

### 3. WAP 对数收益率滚动波动率

- **log_return_wap_1_vol_60 / 180 / 360**: 第一档 WAP 对数收益率多窗口滚动波动率
  - 计算：`RollingStd(log_return_wap_1, w)`，`w ∈ {60, 180, 360}`
  - 含义：不同时间尺度下第一档 WAP 对数收益率的标准差
  - 用途：衡量短期到中期的微观价格扰动强弱

说明：

- 当前实现中的持续时长按连续快照数统计，而不是物理秒数。
- 当前实现同时生成 `60 / 180 / 360` 三档窗口。
- 对应滚动因子在前 `w` 行可能为空，因为滚动窗口不足。

---

## 十、订单流失衡因子（Order Flow Imbalance Features）

- **ofi**: 一阶订单流失衡
  - 计算：`1(bid1_price[t] >= bid1_price[t-1]) * bid1_size[t] - 1(bid1_price[t] <= bid1_price[t-1]) * bid1_size[t-1] - 1(ask1_price[t] <= ask1_price[t-1]) * ask1_size[t] + 1(ask1_price[t] >= ask1_price[t-1]) * ask1_size[t-1]`
  - 含义：相邻快照下，最优买卖价位变化所对应的净订单流压力
  - 用途：刻画短时买卖力量偏向，是典型高频微观结构信号

- **ofi_60 / 180 / 360**: 多窗口累计订单流失衡
  - 计算：`RollingSum(ofi, w)`，`w ∈ {60, 180, 360}`
  - 含义：不同时间尺度下的累计净订单流压力
  - 用途：衡量短期内订单流的持续方向性

说明：

- 当前实现基于相邻快照的一档 `bid1/ask1` 价格与数量变化构造 OFI。
- 当前实现同时生成 `ofi_60`、`ofi_180`、`ofi_360`。

---

## 十一、盘口斜率与凸性因子（Book Shape Features）

先定义买卖两侧五档累计深度：

- `Q_bid_i = Σ(bid_k_size)`，`k = 1..i`
- `Q_ask_i = Σ(ask_k_size)`，`k = 1..i`

再定义相对最优价的归一化距离：

- `x_bid_i = (bid1_price - bid_i_price) / (bid1_price - bid5_price)`
- `x_ask_i = (ask_i_price - ask1_price) / (ask5_price - ask1_price)`
- `y_bid_i = Q_bid_i / Q_bid_5`
- `y_ask_i = Q_ask_i / Q_ask_5`

### 1. 盘口斜率

- **bid_depth_slope**: 买侧盘口斜率
  - 计算：对 `y_bid_i = α + β * x_bid_i + ε_i` 做线性拟合，其中 `β` 为 `bid_depth_slope`
  - 含义：买侧累计深度随档位距离扩张的速度
  - 用途：判断买盘深度是更集中在近端还是逐步堆积到远端

- **ask_depth_slope**: 卖侧盘口斜率
  - 计算：对 `y_ask_i = α + β * x_ask_i + ε_i` 做线性拟合，其中 `β` 为 `ask_depth_slope`
  - 含义：卖侧累计深度随档位距离扩张的速度
  - 用途：判断卖盘深度分布形态

### 2. 盘口凸性

- **bid_book_convexity**: 买侧盘口凸性
  - 计算：`mean(y_bid_i - x_bid_i)`，`i = 1..5`
  - 含义：买侧累计深度曲线相对对角线 `y = x` 的平均偏离
  - 用途：正值通常表示近端更厚，负值通常表示远端更厚

- **ask_book_convexity**: 卖侧盘口凸性
  - 计算：`mean(y_ask_i - x_ask_i)`，`i = 1..5`
  - 含义：卖侧累计深度曲线相对对角线 `y = x` 的平均偏离
  - 用途：正值通常表示近端更厚，负值通常表示远端更厚

说明：

- 当前实现使用五档累计深度与归一化档位距离进行拟合。
- 当五档价格距离为 0 或该侧总挂单量为 0 时，相关形状因子返回 `0`。

---

## 十二、分层不平衡与队列集中度因子（Depth Balance Features）

定义：

- `B_k = Σ(bid_i_size)`，`i = 1..k`
- `A_k = Σ(ask_i_size)`，`i = 1..k`

### 1. 分层不平衡

- **imbalance_top1**: 一档不平衡
  - 计算：`(B_1 - A_1) / (B_1 + A_1)`
  - 含义：最优一档买卖挂单量的相对失衡程度
  - 用途：反映最靠近撮合位置的挂单力量偏向

- **imbalance_top3**: 三档不平衡
  - 计算：`(B_3 - A_3) / (B_3 + A_3)`
  - 含义：前三档买卖深度的相对失衡程度
  - 用途：反映近端盘口整体压力

- **imbalance_top5**: 五档不平衡
  - 计算：`(B_5 - A_5) / (B_5 + A_5)`
  - 含义：前五档买卖深度的相对失衡程度
  - 用途：反映全五档盘口力量偏向

### 2. 加权深度不平衡

- **weighted_imbalance_inv**: 近端加权深度不平衡
  - 计算：`(Σ((1 / i) * bid_i_size) - Σ((1 / i) * ask_i_size)) / (Σ((1 / i) * bid_i_size) + Σ((1 / i) * ask_i_size))`，`i = 1..5`
  - 含义：对近端档位赋予更高权重后的买卖深度相对失衡程度
  - 用途：更突出最优档附近流动性的偏向

### 3. 队列集中度

- **bid1_queue_concentration**: 买一队列集中度
  - 计算：`bid1_size / buy_volume`
  - 含义：买方总深度中有多少集中在买一
  - 用途：判断买盘流动性是否高度堆积在近端

- **ask1_queue_concentration**: 卖一队列集中度
  - 计算：`ask1_size / sell_volume`
  - 含义：卖方总深度中有多少集中在卖一
  - 用途：判断卖盘流动性是否高度堆积在近端

- **top2_depth_share**: 前两档深度占比
  - 计算：`(bid1_size + bid2_size + ask1_size + ask2_size) / (buy_volume + sell_volume)`
  - 含义：全盘口前两档深度占前五档总深度的比例
  - 用途：衡量流动性是更集中在近端还是更分散到深端

说明：

- 当前实现中的 `imbalance_top5` 与 `volume_imbalance` 使用相同五档总量口径，因此通常会高度相似。
- 若后续需要更强近端权重，可以再扩展指数衰减版本。

---

## 十三、动态盘口微观结构因子（Dynamic Microstructure Features）

- **imbalance_top3_change**: 三档不平衡变化率
  - 计算：`imbalance_top3[t] - imbalance_top3[t-1]`
  - 含义：近端三档买卖失衡在相邻快照间的变化幅度
  - 用途：反映近端盘口力量是否正在快速切换

- **weighted_imbalance_inv_change**: 加权深度不平衡变化率
  - 计算：`weighted_imbalance_inv[t] - weighted_imbalance_inv[t-1]`
  - 含义：近端加权深度失衡在相邻快照间的变化幅度
  - 用途：刻画近端深度偏向的动态变化

- **ofi_zscore_60 / 180 / 360**: OFI 的多窗口滚动标准化
  - 计算：`(ofi - RollingMean(ofi, w)) / RollingStd(ofi, w)`，`w ∈ {60, 180, 360}`
  - 含义：当前 OFI 相对不同时间尺度近期分布的偏离程度
  - 用途：识别异常强的短时订单流冲击

- **bid_depth_slope_change**: 买侧盘口斜率变化率
  - 计算：`bid_depth_slope[t] - bid_depth_slope[t-1]`
  - 含义：买侧深度曲线形状的相邻快照变化
  - 用途：衡量买盘从近端堆积到远端堆积的切换速度

- **ask_depth_slope_change**: 卖侧盘口斜率变化率
  - 计算：`ask_depth_slope[t] - ask_depth_slope[t-1]`
  - 含义：卖侧深度曲线形状的相邻快照变化
  - 用途：衡量卖盘形态变化速度

说明：

- `*_change` 第一行通常为空，因为不存在 `t-1`。
- 当前实现同时生成 `ofi_zscore_60`、`ofi_zscore_180`、`ofi_zscore_360`。
- 对应滚动因子在前 `w` 行可能为空，因为滚动窗口不足。

---

## 十四、波动率因子（Volatility Features）

- **log_return_wap_2_vol_60 / 180 / 360**: 第二档 WAP 对数收益率滚动波动率
  - 计算：`RollingStd(log_return_wap_2, w)`，`w ∈ {60, 180, 360}`
  - 含义：第二档 WAP 对数收益率在不同时间尺度下的标准差
  - 用途：衡量次优档位均衡价格的短期波动强度

- **log_return_bid1_price_vol_60 / 180 / 360**: 买一价对数收益率滚动波动率
  - 计算：`RollingStd(log_return_bid1_price, w)`，`w ∈ {60, 180, 360}`
  - 含义：买一价对数收益率在不同时间尺度下的标准差
  - 用途：衡量最优买价的短期扰动强度

- **price_spread_vol_60 / 180 / 360**: 买卖价差滚动波动率
  - 计算：`RollingStd(price_spread, w)`，`w ∈ {60, 180, 360}`
  - 含义：归一化买卖价差在不同时间尺度下的标准差
  - 用途：衡量流动性状态的波动程度

- **ofi_vol_60 / 180 / 360**: 订单流失衡滚动波动率
  - 计算：`RollingStd(ofi, w)`，`w ∈ {60, 180, 360}`
  - 含义：订单流失衡在不同时间尺度下的标准差
  - 用途：衡量订单流冲击强弱的波动程度

说明：

- 当前统一使用 `60 / 180 / 360` 窗口滚动标准差定义波动率。
- `ofi_vol_*` 属于订单流波动率，不是价格波动率。
- 对应滚动因子在前 `w` 行可能为空，因为滚动窗口不足。

---

## 十五、趋势因子（Trend Features）

趋势因子基于以下变量集合：

- `ask1_price`
- `bid1_price`
- `buy_spread`
- `sell_spread`
- `wap_1`
- `wap_2`
- `buy_vwap`
- `sell_vwap`
- `volume`

统一公式：

- `y_trend_w = (y - RollingMean(y, w)) / RollingStd(y, w)`，`w ∈ {60, 180, 360}`

对应输出列：

- 对每个 `w ∈ {60, 180, 360}`，生成：
  `ask1_price_trend_w`、`bid1_price_trend_w`、`buy_spread_trend_w`、`sell_spread_trend_w`、
  `wap_1_trend_w`、`wap_2_trend_w`、`buy_vwap_trend_w`、`sell_vwap_trend_w`、`volume_trend_w`

说明：

- 当前实现分母使用 `RollingStd(y, w) + 1e-8`，用于避免除零。
- 对应滚动因子在前 `w` 行可能为空，因为滚动窗口不足。

---

## 十六、因子应用说明

### 1. 因子类型分类

- **价格类因子**：订单簿价格、K线价格、WAP、VWAP
- **数量类因子**：订单量、归一化订单量、买卖总量
- **比率类因子**：价差、成交量不平衡度、分层不平衡、队列集中度、K线归一化比率
- **动态类因子**：对数收益率、稳定性因子、波动率因子、OFI、动态盘口因子、趋势因子

### 2. 常见应用场景

- **流动性分析**：`price_spread`、`volume`、`buy_spread`、`sell_spread`
- **盘口深度平衡分析**：`imbalance_top1`、`imbalance_top3`、`weighted_imbalance_inv`
- **市场微观结构分析**：订单簿价格数量、`wap_1`、`wap_2`、`buy_vwap`、`sell_vwap`、`ofi`
- **成交与持仓活跃度分析**：`trade_volume_delta`、`turnover_delta`、`avg_trade_price_bias`、`open_interest_change`
- **价格预测**：`volume_imbalance`、`log_return_*`、`*_vol_{60,180,360}`、`ofi_zscore_{60,180,360}`、`*_trend_{60,180,360}`、K线特征
- **流动性形状分析**：`best_spread_duration`、`best_quote_duration`、`bid_depth_slope`、`ask_depth_slope`、`*_book_convexity`、`top2_depth_share`
- **风险管理**：`klen`、`price_spread`、`volume_imbalance`、`log_return_wap_1_vol_{60,180,360}`

### 3. 注意事项

- 对数收益率、稳定性、OFI 和趋势因子都依赖历史序列。
- 趋势因子是 `60 / 180 / 360` 窗口滚动标准化结果。
- `max_oc` 和 `min_oc` 是中间变量，不属于最终输出列。
