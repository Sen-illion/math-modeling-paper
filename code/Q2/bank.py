"""缓存因果点预测及其分位偏置变体。

第 D 日的点预测（扩展窗口 XGBoost 负荷预测与近 7 日同刻光伏预测）仅依赖
D 日以前的数据，因此对所有策略都相同。重新拟合约需 160 秒，故根据原始附件
和模型设置的指纹将其缓存到磁盘。

用于修正第 D 日预测的残差分位数同样仅由 D 日以前的数据构造，因此可预先计算
整套分位数阶梯，并在回放过程中按 (q, day) 索引。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    ATTACHMENT1_XLSX,
    ATTACHMENT2_XLSX,
    CLEAN_DIR,
    FEATURE_COLS,
    FORECAST_BANK_NPZ,
    N_INTERVALS,
    XGB_PARAMS,
)
from forecast import apply_pv_night_zero, clip_nonneg, weekly_dow

BANK_MODEL = "xgb_expanding"
BANK_PV_SOURCE = "baseline_7d"
BANK_FORMAT = 2


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bank_fingerprint(start_idx: int, end_idx: int) -> str:
    payload = {
        "format": BANK_FORMAT,
        "model": BANK_MODEL,
        "pv_source": BANK_PV_SOURCE,
        "start_idx": int(start_idx),
        "end_idx": int(end_idx),
        "xgb_params": XGB_PARAMS,
        "feature_cols": FEATURE_COLS,
        "attachment1": _file_digest(ATTACHMENT1_XLSX),
        "attachment2": _file_digest(ATTACHMENT2_XLSX),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _to_arrays(point: list[dict]) -> dict:
    return {
        "days": np.array([int(p["day"]) for p in point], dtype=np.int32),
        "dates": np.array([str(p["date"]) for p in point]),
        "load_kw": np.vstack([np.asarray(p["load_kw"], dtype=float) for p in point]),
        "load_weekly_kw": np.vstack([np.asarray(p["load_weekly_kw"], dtype=float) for p in point]),
        "pv_kw": np.vstack([np.asarray(p["pv_kw"], dtype=float) for p in point]),
        "xgb_used": np.array([bool(p["xgb_used"]) for p in point]),
    }


def _from_arrays(data) -> list[dict]:
    days = data["days"]
    dates = data["dates"]
    load_kw = data["load_kw"]
    weekly = data["load_weekly_kw"]
    pv_kw = data["pv_kw"]
    xgb_used = data["xgb_used"]
    return [
        {
            "day": int(days[i]),
            "date": str(dates[i]),
            "load_kw": np.asarray(load_kw[i], dtype=float),
            "load_weekly_kw": np.asarray(weekly[i], dtype=float),
            "pv_kw": np.asarray(pv_kw[i], dtype=float),
            "xgb_used": bool(xgb_used[i]),
            "pv_source": BANK_PV_SOURCE,
        }
        for i in range(len(days))
    ]


def load_point_bank(
    prices: pd.DataFrame,
    year: dict,
    start_idx: int,
    end_idx: int,
    load_panel: pd.DataFrame | None = None,
    pv_panel: pd.DataFrame | None = None,
    refresh: bool = False,
) -> list[dict]:
    """获取 start_idx 至 end_idx 各日的点预测；指纹匹配时从缓存读取。"""
    from forecast import precompute_panel
    from run_q2 import collect_forecasts

    want = bank_fingerprint(start_idx, end_idx)
    if not refresh and FORECAST_BANK_NPZ.exists():
        with np.load(FORECAST_BANK_NPZ, allow_pickle=False) as data:
            if str(data["fingerprint"]) == want:
                point = _from_arrays(data)
                print(f"forecast bank: cache hit ({len(point)} days) {FORECAST_BANK_NPZ}", flush=True)
                return point
        print("forecast bank: fingerprint changed, refitting", flush=True)

    if load_panel is None:
        print("forecast bank: precomputing causal feature panels...", flush=True)
        load_panel = precompute_panel(year["load_kw"], year["dates"])
    if pv_panel is None:
        pv_panel = precompute_panel(year["pv_kw"], year["dates"])
    t0 = time.perf_counter()
    point, _ = collect_forecasts(
        BANK_MODEL,
        prices,
        year,
        start_idx,
        end_idx,
        load_panel,
        pv_panel,
        cache={},
        pv_source=BANK_PV_SOURCE,
    )
    print(f"forecast bank: fitted in {time.perf_counter() - t0:.1f}s", flush=True)
    fallback = prices["typical_load_kw"].to_numpy(dtype=float) if "typical_load_kw" in prices.columns else year["load_kw"][0]
    dates = year["dates"]
    for pred in point:
        day = int(pred["day"])
        pred["load_weekly_kw"] = weekly_dow(year["load_kw"], day, dates, fallback)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(FORECAST_BANK_NPZ, fingerprint=want, **_to_arrays(point))
    print("forecast bank: cached to", FORECAST_BANK_NPZ, flush=True)
    return point


def slot_quantile(residuals: list[np.ndarray], q) -> np.ndarray:
    """计算各时段的残差分位数；q 可以是标量或长度为 144 的向量。"""
    stacked = np.vstack(residuals)
    if np.isscalar(q):
        return np.quantile(stacked, float(q), axis=0)
    q = np.asarray(q, dtype=float)
    return np.array([np.quantile(stacked[:, s], q[s]) for s in range(stacked.shape[1])])


def season_id(stamp) -> int:
    """气象季节编号：0=冬季，1=春季，2=夏季，3=秋季。"""
    month = int(pd.Timestamp(stamp).month)
    if month in (12, 1, 2):
        return 0
    if month in (3, 4, 5):
        return 1
    if month in (6, 7, 8):
        return 2
    return 3


def _pool_arrays(
    history: list[tuple[int, np.ndarray]],
    day: int,
    dates: pd.Series,
    pool: dict | None,
) -> list[np.ndarray]:
    """获取第 D 日的因果残差子集；默认使用扩展窗口，即 D 日以前的全部日期。"""
    if not history:
        return []
    spec = pool or {"mode": "expanding"}
    mode = spec.get("mode", "expanding")
    if mode == "expanding":
        picked = history
    elif mode == "rolling":
        picked = history[-int(spec["window"]) :]
    elif mode == "season":
        want = season_id(dates.iloc[day])
        picked = [(d, arr) for d, arr in history if season_id(dates.iloc[d]) == want]
    elif mode == "month":
        month = int(pd.Timestamp(dates.iloc[day]).month)
        picked = [(d, arr) for d, arr in history if int(pd.Timestamp(dates.iloc[d]).month) == month]
        if len(picked) < int(spec.get("min_days", 14)):
            picked = history
    else:
        raise ValueError(f"unknown residual pool mode {mode}")
    return [arr for _, arr in picked]


def bias_bank(point: list[dict], year: dict, q_load, q_pv, pool: dict | None = None) -> list[dict]:
    """使用因果残差分位数修正点预测；残差仅取自 D 日以前的数据。"""
    dates = year["dates"]
    load_hist: list[tuple[int, np.ndarray]] = []
    pv_hist: list[tuple[int, np.ndarray]] = []
    out = []
    for pred in point:
        day = int(pred["day"])
        load_plan = np.asarray(pred["load_kw"], dtype=float).copy()
        pv_plan = np.asarray(pred["pv_kw"], dtype=float).copy()
        load_pool = _pool_arrays(load_hist, day, dates, pool)
        pv_pool = _pool_arrays(pv_hist, day, dates, pool)
        if q_load is not None and load_pool:
            load_plan = load_plan + slot_quantile(load_pool, q_load)
        if q_pv is not None and pv_pool:
            pv_plan = pv_plan + slot_quantile(pv_pool, q_pv)
        load_hist.append((day, year["load_kw"][day] - pred["load_kw"]))
        pv_hist.append((day, year["pv_kw"][day] - pred["pv_kw"]))
        row = dict(pred)
        row["load_kw"] = clip_nonneg(load_plan)
        row["pv_kw"] = clip_nonneg(apply_pv_night_zero(pv_plan, year["pv_kw"][:day]))
        row["resid_pool_n"] = int(len(load_pool))
        out.append(row)
    return out


def mix_point(point: list[dict], lam: float) -> list[dict]:
    """在点预测层融合周周期负荷与 XGBoost 负荷；lam=1 表示仅使用 XGBoost。"""
    lam = float(lam)
    out = []
    for pred in point:
        row = dict(pred)
        xgb = np.asarray(pred["load_kw"], dtype=float)
        weekly = np.asarray(pred["load_weekly_kw"], dtype=float)
        row["load_kw"] = clip_nonneg((1.0 - lam) * weekly + lam * xgb)
        row["load_mix"] = lam
        out.append(row)
    return out


def bias_net_bank(point: list[dict], year: dict, alpha: float, window: int | None = None) -> list[dict]:
    """保守净负荷分位修正：直接对 L-P 使用一个残差，不拆分负荷与光伏。

    window=None 时使用全部已完成日期，即扩展窗口；window 为正数时仅保留最近
    window 个已完成日期的残差，可对应 W=7 的净负荷分位方案。
    """
    net_resid: list[np.ndarray] = []
    out = []
    for pred in point:
        day = int(pred["day"])
        load_hat = np.asarray(pred["load_kw"], dtype=float)
        pv_hat = np.asarray(pred["pv_kw"], dtype=float)
        net_hat = load_hat - pv_hat
        net_plan = net_hat.copy()
        if net_resid:
            pool = net_resid[-int(window) :] if window else net_resid
            net_plan = net_hat + slot_quantile(pool, alpha)
        pv_plan = clip_nonneg(apply_pv_night_zero(pv_hat.copy(), year["pv_kw"][:day]))
        load_plan = clip_nonneg(pv_plan + net_plan)
        net_resid.append((year["load_kw"][day] - year["pv_kw"][day]) - net_hat)
        row = dict(pred)
        row["load_kw"] = load_plan
        row["pv_kw"] = pv_plan
        row["risk"] = "net"
        row["alpha"] = float(alpha)
        row["resid_window"] = None if window is None else int(window)
        out.append(row)
    return out


def ladder_banks(point: list[dict], year: dict, ladder, pool: dict | None = None) -> dict[float, list[dict]]:
    """为每个分位阶梯建立一个偏置预测库，以 q_load 为键，q_pv 取 1-q_load。"""
    return {
        float(q): bias_bank(point, year, float(q), round(1.0 - float(q), 6), pool=pool) for q in ladder
    }


def point_residual_history(point: list[dict], year: dict) -> dict[int, dict]:
    """生成以 kW 为单位的逐日点预测残差，用于构造因果状态特征。"""
    out = {}
    for pred in point:
        day = int(pred["day"])
        out[day] = {
            "load": year["load_kw"][day] - np.asarray(pred["load_kw"], dtype=float),
            "pv": year["pv_kw"][day] - np.asarray(pred["pv_kw"], dtype=float),
        }
    return out


def check_length(bank: list[dict]) -> None:
    for pred in bank:
        if len(pred["load_kw"]) != N_INTERVALS or len(pred["pv_kw"]) != N_INTERVALS:
            raise ValueError(f"{pred['date']}: forecast is not {N_INTERVALS} slots")
