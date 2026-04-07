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

- `max_oc` 和 `min_oc` 为中间变量，不作为最终输出因子列。

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

## 5. 价差与量能特征

```text
buy_spread  = abs(bid1_price - bid5_price)
sell_spread = abs(ask1_price - ask5_price)
price_spread = 2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)

buy_volume  = bid1_size + bid2_size + bid3_size + bid4_size + bid5_size
sell_volume = ask1_size + ask2_size + ask3_size + ask4_size + ask5_size

volume_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
```

## 6. VWAP 特征

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

## 7. 对数收益率特征

```text
log_return_bid1_price = log(bid1_price[t] / bid1_price[t-1])
log_return_bid2_price = log(bid2_price[t] / bid2_price[t-1])
log_return_ask1_price = log(ask1_price[t] / ask1_price[t-1])
log_return_ask2_price = log(ask2_price[t] / ask2_price[t-1])

log_return_wap_1 = log(wap_1[t] / wap_1[t-1])
log_return_wap_2 = log(wap_2[t] / wap_2[t-1])
```

说明：

- 这里的 `log_return_*` 基于价格序列，不基于 `*_size_n`。

## 8. 稳定性特征

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
- 当前实现同时生成 `60 / 180 / 360` 三档窗口。
- 对应滚动因子在前 `w` 行可能为空，因为滚动窗口不足。

## 9. 订单流失衡特征

```text
e_b = 1(bid1_price[t] >= bid1_price[t-1]) * bid1_size[t]
    - 1(bid1_price[t] <= bid1_price[t-1]) * bid1_size[t-1]

e_a = 1(ask1_price[t] <= ask1_price[t-1]) * ask1_size[t]
    - 1(ask1_price[t] >= ask1_price[t-1]) * ask1_size[t-1]

ofi = e_b - e_a
for w in {60, 180, 360}:
  ofi_w = RollingSum(ofi, w)
```

## 10. 盘口斜率与凸性特征

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

说明：

- 正值通常表示近端更厚，负值通常表示远端更厚。

## 11. 分层不平衡与队列集中度特征

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
- `weighted_imbalance_inv` 对近端档位赋予更高权重，当前使用 `w_i = 1 / i`。

## 12. 动态盘口微观结构特征

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

说明：

- `*_change` 为一阶差分，反映盘口状态变化速度。
- 当前实现同时生成 `ofi_zscore_60`、`ofi_zscore_180`、`ofi_zscore_360`。

## 13. 波动率特征

```text
for w in {60, 180, 360}:
  log_return_wap_2_vol_w = RollingStd(log_return_wap_2, w)
  log_return_bid1_price_vol_w = RollingStd(log_return_bid1_price, w)
  price_spread_vol_w = RollingStd(price_spread, w)
  ofi_vol_w = RollingStd(ofi, w)
```

说明：

- 当前统一使用 `60 / 180 / 360` 窗口滚动标准差定义波动率。
- `ofi_vol_*` 描述的是订单流波动率，不是价格波动率。

## 14. 趋势特征

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

## 15. 最终输出因子列表

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
buy_vwap, sell_vwap,
log_return_bid1_price, log_return_bid2_price,
log_return_ask1_price, log_return_ask2_price,
log_return_wap_1, log_return_wap_2,
best_spread_duration, best_quote_duration,
log_return_wap_1_vol_{60,180,360},
ofi, ofi_{60,180,360},
bid_depth_slope, ask_depth_slope,
bid_book_convexity, ask_book_convexity,
imbalance_top3_change, weighted_imbalance_inv_change,
ofi_zscore_{60,180,360},
bid_depth_slope_change, ask_depth_slope_change,
log_return_wap_2_vol_{60,180,360},
log_return_bid1_price_vol_{60,180,360},
price_spread_vol_{60,180,360},
ofi_vol_{60,180,360},
ask1_price_trend_{60,180,360}, bid1_price_trend_{60,180,360},
buy_spread_trend_{60,180,360}, sell_spread_trend_{60,180,360},
wap_1_trend_{60,180,360}, wap_2_trend_{60,180,360},
buy_vwap_trend_{60,180,360}, sell_vwap_trend_{60,180,360},
volume_trend_{60,180,360}
```
