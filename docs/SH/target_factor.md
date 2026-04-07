# Target Factor

## 1. 基础输入字段

### 五档价格与数量

- `ask1_price` ~ `ask5_price`
- `ask1_size` ~ `ask5_size`
- `bid1_price` ~ `bid5_price`
- `bid1_size` ~ `bid5_size`

### K线价格

- `open_price`
- `high_price`
- `low_price`
- `close_price`

### 成交与持仓快照

- `total_trade_volume`
- `turnover`
- `open_interest`

说明：

- `total_trade_volume` 与 `turnover` 都是截至当前快照时点的累计值，不是窗口内新增量。
- `open_interest` 是当前时点的持仓量快照。
- 成交类衍生因子先做相邻快照差分，再进入滚动统计。

## 2. K线特征

```text
max_oc = max(open_price, close_price)
min_oc = min(open_price, close_price)

kmid  = close_price - open_price
kmid2 = (close_price - open_price) / (high_price - low_price)

klen  = high_price - low_price

kup   = high_price - max_oc
kup2  = (high_price - max_oc) / (high_price - low_price)

klow  = min_oc - low_price
klow2 = (min_oc - low_price) / (high_price - low_price)

ksft  = 2 * close_price - high_price - low_price
ksft2 = ksft / (high_price - low_price)
```

说明：

- `max_oc` 和 `min_oc` 为中间变量，不作为最终输出因子。

## 3. 订单簿归一化特征

```text
volume = bid1_size + bid2_size + bid3_size + bid4_size + bid5_size
       + ask1_size + ask2_size + ask3_size + ask4_size + ask5_size

bid1_size_n = bid1_size / volume
bid2_size_n = bid2_size / volume
bid3_size_n = bid3_size / volume
bid4_size_n = bid4_size / volume
bid5_size_n = bid5_size / volume

ask1_size_n = ask1_size / volume
ask2_size_n = ask2_size / volume
ask3_size_n = ask3_size / volume
ask4_size_n = ask4_size / volume
ask5_size_n = ask5_size / volume
```

## 4. WAP 特征

```text
wap_1 = (ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)
wap_2 = (ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)

wap_balance = abs(wap_1 - wap_2)
```

## 5. 成交与持仓快照衍生特征

以下差分默认按同一 `date / contract` 分组，避免跨日累计值串联。

```text
trade_volume_delta = max(total_trade_volume[t] - total_trade_volume[t-1], 0)
turnover_delta     = max(turnover[t] - turnover[t-1], 0)

open_interest_change =
  open_interest[t] - open_interest[t-1]

open_interest_change_ratio =
  open_interest_change / abs(open_interest[t-1])

open_interest_change_per_trade =
  open_interest_change / trade_volume_delta

avg_trade_price =
  if trade_volume_delta > 0
  then turnover_delta / trade_volume_delta
  else close_price

avg_trade_price_bias =
  (avg_trade_price - wap_1) / wap_1

avg_trade_price_bias_change =
  avg_trade_price_bias[t] - avg_trade_price_bias[t-1]
```

对于滚动窗口 `w ∈ {60, 180, 360}`：

```text
trade_volume_delta_vol_w   = RollingStd(trade_volume_delta, w)
turnover_delta_vol_w       = RollingStd(turnover_delta, w)
avg_trade_price_bias_vol_w = RollingStd(avg_trade_price_bias, w)
open_interest_change_vol_w = RollingStd(open_interest_change, w)

trade_volume_delta_zscore_w =
  (trade_volume_delta - RollingMean(trade_volume_delta, w))
  / RollingStd(trade_volume_delta, w)

turnover_delta_zscore_w =
  (turnover_delta - RollingMean(turnover_delta, w))
  / RollingStd(turnover_delta, w)

avg_trade_price_bias_zscore_w =
  (avg_trade_price_bias - RollingMean(avg_trade_price_bias, w))
  / RollingStd(avg_trade_price_bias, w)

open_interest_change_zscore_w =
  (open_interest_change - RollingMean(open_interest_change, w))
  / RollingStd(open_interest_change, w)

signed_trade_pressure_w =
  sign(avg_trade_price_bias) * trade_volume_delta_zscore_w

signed_open_interest_pressure_w =
  sign(avg_trade_price_bias) * open_interest_change_zscore_w

trade_ofi_resonance_w =
  avg_trade_price_bias_zscore_w * ofi_zscore_w

trade_volume_delta_slope_w =
  (trade_volume_delta[t] - trade_volume_delta[t-w]) / w

turnover_delta_slope_w =
  (turnover_delta[t] - turnover_delta[t-w]) / w

avg_trade_price_bias_slope_w =
  (avg_trade_price_bias[t] - avg_trade_price_bias[t-w]) / w

open_interest_slope_w =
  (open_interest[t] - open_interest[t-w]) / w
```

## 6. 价差与量能特征

```text
buy_spread  = abs(bid1_price - bid5_price)
sell_spread = abs(ask1_price - ask5_price)
price_spread = 2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)

buy_volume  = bid1_size + bid2_size + bid3_size + bid4_size + bid5_size
sell_volume = ask1_size + ask2_size + ask3_size + ask4_size + ask5_size

volume_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
```

## 7. VWAP 特征

```text
sell_vwap = ask1_size_n * ask1_price
          + ask2_size_n * ask2_price
          + ask3_size_n * ask3_price
          + ask4_size_n * ask4_price
          + ask5_size_n * ask5_price

buy_vwap  = bid1_size_n * bid1_price
          + bid2_size_n * bid2_price
          + bid3_size_n * bid3_price
          + bid4_size_n * bid4_price
          + bid5_size_n * bid5_price
```

## 8. 对数收益率特征

```text
log_return_bid1_price = log(bid1_price[t] / bid1_price[t-1])
log_return_bid2_price = log(bid2_price[t] / bid2_price[t-1])
log_return_ask1_price = log(ask1_price[t] / ask1_price[t-1])
log_return_ask2_price = log(ask2_price[t] / ask2_price[t-1])

log_return_wap_1 = log(wap_1[t] / wap_1[t-1])
log_return_wap_2 = log(wap_2[t] / wap_2[t-1])
```

说明：

- `log_return_*` 基于价格序列，不基于 `*_size_n`。

## 9. 稳定性特征

```text
best_spread_duration =
  if price_spread[t] == price_spread[t-1]
  then best_spread_duration[t-1] + 1
  else 1

best_quote_duration =
  if bid1_price[t] == bid1_price[t-1] and ask1_price[t] == ask1_price[t-1]
  then best_quote_duration[t-1] + 1
  else 1

for w in {60, 180, 360}:
  log_return_wap_1_vol_w = RollingStd(log_return_wap_1, w)
```

说明：

- `best_*_duration` 当前按连续快照数统计。

## 10. 订单流失衡特征

```text
e_b = 1(bid1_price[t] >= bid1_price[t-1]) * bid1_size[t]
    - 1(bid1_price[t] <= bid1_price[t-1]) * bid1_size[t-1]

e_a = 1(ask1_price[t] <= ask1_price[t-1]) * ask1_size[t]
    - 1(ask1_price[t] >= ask1_price[t-1]) * ask1_size[t-1]

ofi = e_b - e_a

for w in {60, 180, 360}:
  ofi_w = RollingSum(ofi, w)
```

## 11. 盘口斜率与凸性特征

先定义五档累计深度：

```text
Q_bid_i = Σ(bidk_size), k = 1..i
Q_ask_i = Σ(askk_size), k = 1..i
```

以及相对最优价的归一化距离：

```text
x_bid_i = (bid1_price - bidi_price) / (bid1_price - bid5_price)
x_ask_i = (aski_price - ask1_price) / (ask5_price - ask1_price)

y_bid_i = Q_bid_i / Q_bid_5
y_ask_i = Q_ask_i / Q_ask_5
```

对 `x_i` 与 `y_i` 做线性拟合：

```text
y_i = alpha + beta * x_i + epsilon_i
```

对应输出列：

- `bid_depth_slope`
- `ask_depth_slope`

凸性定义为归一化累计深度曲线相对对角线 `y = x` 的平均偏离：

```text
bid_book_convexity = mean(y_bid_i - x_bid_i), i = 1..5
ask_book_convexity = mean(y_ask_i - x_ask_i), i = 1..5
```

## 12. 分层不平衡与队列集中度特征

```text
B_1 = bid1_size
A_1 = ask1_size

B_3 = bid1_size + bid2_size + bid3_size
A_3 = ask1_size + ask2_size + ask3_size

B_5 = buy_volume
A_5 = sell_volume

imbalance_top1 = (B_1 - A_1) / (B_1 + A_1)
imbalance_top3 = (B_3 - A_3) / (B_3 + A_3)
imbalance_top5 = (B_5 - A_5) / (B_5 + A_5)

weighted_imbalance_inv =
  (Σ((1 / i) * bidi_size) - Σ((1 / i) * aski_size))
  / (Σ((1 / i) * bidi_size) + Σ((1 / i) * aski_size))

bid1_queue_concentration = bid1_size / buy_volume
ask1_queue_concentration = ask1_size / sell_volume

top2_depth_share =
  (bid1_size + bid2_size + ask1_size + ask2_size)
  / (buy_volume + sell_volume)
```

说明：

- `imbalance_top5` 与五档总量口径下的 `volume_imbalance` 本质一致。

## 13. 动态盘口微观结构特征

```text
imbalance_top3_change = imbalance_top3[t] - imbalance_top3[t-1]

weighted_imbalance_inv_change =
  weighted_imbalance_inv[t] - weighted_imbalance_inv[t-1]

for w in {60, 180, 360}:
  ofi_zscore_w =
    (ofi - RollingMean(ofi, w)) / RollingStd(ofi, w)

bid_depth_slope_change = bid_depth_slope[t] - bid_depth_slope[t-1]
ask_depth_slope_change = ask_depth_slope[t] - ask_depth_slope[t-1]
```

## 14. 波动率特征

```text
for w in {60, 180, 360}:
  log_return_wap_1_vol_w = RollingStd(log_return_wap_1, w)
  log_return_wap_2_vol_w = RollingStd(log_return_wap_2, w)
  log_return_bid1_price_vol_w = RollingStd(log_return_bid1_price, w)
  price_spread_vol_w = RollingStd(price_spread, w)
  ofi_vol_w = RollingStd(ofi, w)
```

说明：

- `ofi_vol_*` 描述的是订单流波动率，不是价格波动率。

## 15. 趋势特征

```text
Y = [
  ask1_price,
  bid1_price,
  buy_spread,
  sell_spread,
  wap_1,
  wap_2,
  buy_vwap,
  sell_vwap,
  volume
]

for w in {60, 180, 360}:
  y_trend_w = (y - RollingMean(y, w)) / RollingStd(y, w)
```

对应输出列：

- 对每个 `w ∈ {60, 180, 360}`，生成
  `ask1_price_trend_w`、`bid1_price_trend_w`、`buy_spread_trend_w`、`sell_spread_trend_w`、
  `wap_1_trend_w`、`wap_2_trend_w`、`buy_vwap_trend_w`、`sell_vwap_trend_w`、`volume_trend_w`

## 16. 最终输出因子列表

```text
kmid, kmid2, klen, kup, kup2, klow, klow2, ksft, ksft2,
volume,
bid1_size_n, bid2_size_n, bid3_size_n, bid4_size_n, bid5_size_n,
ask1_size_n, ask2_size_n, ask3_size_n, ask4_size_n, ask5_size_n,
wap_1, wap_2, wap_balance,
buy_spread, sell_spread, price_spread,
buy_volume, sell_volume, volume_imbalance,
imbalance_top1, imbalance_top3, imbalance_top5,
weighted_imbalance_inv,
bid1_queue_concentration, ask1_queue_concentration,
top2_depth_share,
trade_volume_delta, turnover_delta,
avg_trade_price, avg_trade_price_bias, avg_trade_price_bias_change,
open_interest_change, open_interest_change_ratio,
open_interest_change_per_trade,
buy_vwap, sell_vwap,
log_return_bid1_price, log_return_bid2_price,
log_return_ask1_price, log_return_ask2_price,
log_return_wap_1, log_return_wap_2,
best_spread_duration, best_quote_duration,
log_return_wap_1_vol_{60,180,360},
ofi, ofi_{60,180,360},
log_return_wap_2_vol_{60,180,360},
log_return_bid1_price_vol_{60,180,360},
price_spread_vol_{60,180,360},
ofi_vol_{60,180,360},
bid_depth_slope, ask_depth_slope,
bid_book_convexity, ask_book_convexity,
imbalance_top3_change, weighted_imbalance_inv_change,
ofi_zscore_{60,180,360},
bid_depth_slope_change, ask_depth_slope_change,
trade_volume_delta_vol_{60,180,360},
turnover_delta_vol_{60,180,360},
avg_trade_price_bias_vol_{60,180,360},
open_interest_change_vol_{60,180,360},
trade_volume_delta_zscore_{60,180,360},
turnover_delta_zscore_{60,180,360},
avg_trade_price_bias_zscore_{60,180,360},
open_interest_change_zscore_{60,180,360},
signed_trade_pressure_{60,180,360},
signed_open_interest_pressure_{60,180,360},
trade_ofi_resonance_{60,180,360},
trade_volume_delta_slope_{60,180,360},
turnover_delta_slope_{60,180,360},
avg_trade_price_bias_slope_{60,180,360},
open_interest_slope_{60,180,360},
ask1_price_trend_{60,180,360}, bid1_price_trend_{60,180,360},
buy_spread_trend_{60,180,360}, sell_spread_trend_{60,180,360},
wap_1_trend_{60,180,360}, wap_2_trend_{60,180,360},
buy_vwap_trend_{60,180,360}, sell_vwap_trend_{60,180,360},
volume_trend_{60,180,360}
```
