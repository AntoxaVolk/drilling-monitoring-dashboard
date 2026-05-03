"""
generate_data.py
Генерация синтетических данных параметров бурения (WITS-формат).
Эмулирует поток данных от телеметрической системы MWD/LWD.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def random_walk(start: float, n: int, step: float,
                low: float, high: float) -> np.ndarray:
    """Генерирует случайное блуждание с ограничениями."""
    vals = [start]
    for _ in range(n - 1):
        nxt = vals[-1] + np.random.uniform(-step, step)
        vals.append(np.clip(nxt, low, high))
    return np.array(vals)


def generate_drilling_params(well_id: int = 247,
                             start_md: float = 1700.0,
                             end_md: float = 3250.0,
                             interval_min: float = 1.0,
                             start_time: datetime = None) -> pd.DataFrame:
    """
    Генерирует таблицу параметров бурения с шагом 1 минута.

    Возвращает DataFrame с колонками:
        well_id, ts_utc, md, rop, wob, rpm, torque, flow_rate, spp
    """
    if start_time is None:
        start_time = datetime(2026, 3, 1, 6, 0, 0)

    np.random.seed(7)

    # Базовый РОП: горизонтальный участок 8–20 м/ч
    rop_base = random_walk(14.0, 2000, 1.5, 4.0, 28.0)

    # Смоделировать НПВ: ~8 эпизодов останова бурения
    npt_episodes = np.random.choice(range(100, 1900), size=8, replace=False)
    npt_duration = np.random.randint(3, 25, size=8)  # минуты
    for ep, dur in zip(npt_episodes, npt_duration):
        rop_base[ep:ep+dur] = 0.0

    n = len(rop_base)

    # Накопленная MD
    md = np.zeros(n)
    md[0] = start_md
    for i in range(1, n):
        md[i] = md[i-1] + rop_base[i] / 60.0  # м/мин
    md = np.clip(md, start_md, end_md)

    # Параметры бурения
    wob      = random_walk(12.0, n, 1.0, 2.0, 22.0)
    rpm      = random_walk(85.0, n, 5.0, 40.0, 130.0).astype(int)
    torque   = random_walk(13.0, n, 1.5, 3.0, 24.0)
    flow_rate= random_walk(32.0, n, 1.0, 18.0, 42.0)
    spp      = random_walk(187.0, n, 4.0, 80.0, 280.0)

    # Аномалия давления (признак ГНВП) в одном случайном эпизоде
    spike_idx = np.random.randint(400, 1600)
    spp[spike_idx:spike_idx+8] += np.linspace(0, 35, 8)

    ts = [start_time + timedelta(minutes=i*interval_min) for i in range(n)]

    df = pd.DataFrame({
        'well_id'   : well_id,
        'ts_utc'    : ts,
        'md'        : np.round(md, 2),
        'rop'       : np.round(rop_base, 2),
        'wob'       : np.round(wob, 2),
        'rpm'       : rpm,
        'torque'    : np.round(torque, 2),
        'flow_rate' : np.round(flow_rate, 2),
        'spp'       : np.round(spp, 1),
    })

    return df


def detect_pressure_anomaly(df: pd.DataFrame,
                             threshold: float = 20.0,
                             window: int = 5) -> pd.DataFrame:
    """
    Выявляет резкий рост давления СПП — возможный признак ГНВП.

    Параметры:
        threshold : порог роста давления (бар) за window минут
        window    : скользящее окно (минуты)
    """
    df = df.copy()
    df['spp_delta'] = df['spp'].diff(periods=window)
    anomalies = df[df['spp_delta'] > threshold].copy()
    anomalies['alert_type'] = 'ГНВП-риск'
    anomalies['alert_text'] = (
        'Рост СПП на ' + anomalies['spp_delta'].round(1).astype(str) + ' бар за ' + str(window) + ' мин'
    )
    return anomalies[['ts_utc', 'md', 'spp', 'spp_delta', 'alert_type', 'alert_text']]


def calc_npt_report(df: pd.DataFrame) -> pd.DataFrame:
    """Рассчитывает НПВ (непроизводительное время) по суткам."""
    df = df.copy()
    df['date'] = pd.to_datetime(df['ts_utc']).dt.date
    df['is_npt'] = (df['rop'] == 0).astype(int)

    report = df.groupby('date').agg(
        total_records=('is_npt', 'count'),
        npt_minutes=('is_npt', 'sum'),
        avg_rop=('rop', lambda x: x[x > 0].mean()),
        max_spp=('spp', 'max')
    ).reset_index()

    report['npt_pct'] = (report['npt_minutes'] / report['total_records'] * 100).round(1)
    report['avg_rop'] = report['avg_rop'].round(2)

    return report


if __name__ == "__main__":
    print("=== Генерация данных параметров бурения ===\n")

    df = generate_drilling_params()
    print(f"Записей сгенерировано : {len(df)}")
    print(f"Период                : {df['ts_utc'].min()} → {df['ts_utc'].max()}")
    print(f"MD диапазон           : {df['md'].min():.0f} – {df['md'].max():.0f} м")
    print(f"Средний РОП (бурение) : {df[df['rop']>0]['rop'].mean():.1f} м/ч\n")

    # Сохранить данные
    df.to_csv("drilling_params.csv", index=False)
    print("Данные сохранены: drilling_params.csv")

    # Аномалии давления
    print("\n=== Аномалии давления (ГНВП-риск) ===")
    anomalies = detect_pressure_anomaly(df)
    if len(anomalies):
        print(anomalies[['ts_utc', 'md', 'spp', 'spp_delta', 'alert_text']].to_string(index=False))
    else:
        print("Аномалий не выявлено.")

    # НПВ-отчёт
    print("\n=== НПВ по суткам ===")
    npt = calc_npt_report(df)
    print(npt[['date', 'npt_minutes', 'npt_pct', 'avg_rop', 'max_spp']].to_string(index=False))
    npt.to_csv("npt_report.csv", index=False)
    print("\nОтчёт сохранён: npt_report.csv")
