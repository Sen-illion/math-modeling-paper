"""0:00 因果电价预测：扩展窗口同刻均值、星期残差与近 7 日残差均值。"""

from __future__ import annotations

import numpy as np

N_SLOTS = 144
N_WEEKDAYS = 7
RECENT_LAGS = 7
RHO_FROZEN = 1.0


def forecast_hat0(
    price: np.ndarray,
    dow: np.ndarray,
    cold_start: np.ndarray,
) -> dict[str, np.ndarray]:
    """由历史同刻均值、星期残差和近 7 日等权残差均值构造预测。

    第 0 日的 b 仅使用附件 1 的冷启动价格曲线；此后 b 使用历史真实价格。
    """
    n_days, n_slots = price.shape
    if n_slots != N_SLOTS:
        raise ValueError(f"expected {N_SLOTS} slots")
    cold = np.asarray(cold_start, dtype=float).reshape(-1)
    if cold.shape != (n_slots,):
        raise ValueError("cold_start must be a 144-slot curve")

    b = np.zeros_like(price)
    r = np.zeros_like(price)
    e = np.zeros_like(price)
    delta_week = np.zeros_like(price)
    delta_recent = np.zeros_like(price)
    hat_c = np.zeros_like(price)
    n_base_used = np.zeros(n_days, dtype=int)
    n_week_used = np.zeros(n_days, dtype=int)
    n_recent_used = np.zeros(n_days, dtype=int)

    sum_p = np.zeros(n_slots, dtype=float)
    cnt_p = 0
    sum_r_w = np.zeros((N_WEEKDAYS, n_slots), dtype=float)
    cnt_w = np.zeros(N_WEEKDAYS, dtype=int)

    for d in range(n_days):
        b[d] = sum_p / cnt_p if cnt_p > 0 else cold
        w = int(dow[d])
        dw = sum_r_w[w] / cnt_w[w] if cnt_w[w] > 0 else np.zeros(n_slots)
        rec = np.zeros(n_slots, dtype=float)
        n_rec = 0
        for k in range(1, RECENT_LAGS + 1):
            j = d - k
            if j < 0:
                continue
            rec += e[j]
            n_rec += 1
        if n_rec > 0:
            rec /= n_rec
        delta_week[d] = dw
        delta_recent[d] = rec
        n_base_used[d] = int(cnt_p)
        n_week_used[d] = int(cnt_w[w])
        n_recent_used[d] = n_rec
        hat_c[d] = b[d] + dw + rec
        r[d] = price[d] - b[d]
        e[d] = price[d] - b[d] - dw
        sum_p += price[d]
        cnt_p += 1
        sum_r_w[w] += r[d]
        cnt_w[w] += 1

    return {
        "hat0": hat_c,
        "b": b,
        "delta_week": delta_week,
        "delta_recent": delta_recent,
        "n_base_used": n_base_used,
        "n_week_used": n_week_used,
        "n_recent_used": n_recent_used,
        "error0": price - hat_c,
    }
