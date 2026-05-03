"""
lwd_analysis.py
Анализ LWD-кривых (ГК, УЭС) и автоматическая литологическая разбивка.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ─── Пороговые значения (настраиваемые) ──────────────────────────────────────
GR_SANDSTONE_MAX  = 45    # API — нефтеносный песчаник / коллектор
GR_SILTSTONE_MAX  = 75    # API — алевролит
RES_OIL_MIN       = 15.0  # Ом·м — признак нефтенасыщения


def classify_lithology(gr: float, res: float) -> str:
    """Простая литологическая классификация по ГК и УЭС."""
    if gr <= GR_SANDSTONE_MAX and res >= RES_OIL_MIN:
        return "Нефтеносный песчаник"
    elif gr <= GR_SANDSTONE_MAX:
        return "Водонасыщенный песчаник"
    elif gr <= GR_SILTSTONE_MAX:
        return "Алевролит"
    else:
        return "Аргиллит/глина"


LITHO_COLORS = {
    "Нефтеносный песчаник"    : "#f5c842",
    "Водонасыщенный песчаник" : "#4287f5",
    "Алевролит"               : "#c8a87a",
    "Аргиллит/глина"          : "#7a6e5f",
}


def generate_lwd_data(well_id: int = 247,
                      md_start: float = 1600.0,
                      md_end: float = 3250.0,
                      step: float = 0.1) -> pd.DataFrame:
    """Генерирует синтетические LWD-кривые с нефтеносным интервалом."""
    np.random.seed(13)
    mds = np.arange(md_start, md_end + step, step)
    n   = len(mds)

    gr      = np.zeros(n)
    res_deep= np.zeros(n)
    res_med = np.zeros(n)
    res_sh  = np.zeros(n)

    # Нефтеносный горизонт Ач3: 2847–3250 м
    oil_mask = (mds >= 2847) & (mds <= 3250)

    for i, md in enumerate(mds):
        if oil_mask[i]:
            # Коллектор: низкий ГК, высокое сопротивление
            if np.random.random() < 0.70:
                gr[i]       = 18 + np.random.uniform(0, 27)
                res_deep[i] = 25 + np.random.uniform(0, 75)
                res_med[i]  = res_deep[i] * np.random.uniform(0.7, 0.95)
                res_sh[i]   = res_med[i]  * np.random.uniform(0.7, 0.95)
            else:
                # Глинистые прослои внутри горизонта
                gr[i]       = 70 + np.random.uniform(0, 60)
                res_deep[i] = 1.5 + np.random.uniform(0, 3)
                res_med[i]  = res_deep[i] * np.random.uniform(0.8, 1.0)
                res_sh[i]   = res_med[i]  * np.random.uniform(0.8, 1.0)
        else:
            # Покрышка / переходная зона
            gr[i]       = 65 + np.random.uniform(0, 85)
            res_deep[i] = 1.0 + np.random.uniform(0, 5)
            res_med[i]  = res_deep[i] * np.random.uniform(0.75, 1.0)
            res_sh[i]   = res_med[i]  * np.random.uniform(0.75, 1.0)

    df = pd.DataFrame({
        'well_id'  : well_id,
        'md'       : np.round(mds, 2),
        'gr'       : np.round(gr, 1),
        'res_deep' : np.round(res_deep, 2),
        'res_med'  : np.round(res_med, 2),
        'res_sh'   : np.round(res_sh, 2),
    })

    df['lithology'] = df.apply(
        lambda r: classify_lithology(r['gr'], r['res_deep']), axis=1
    )
    return df


def interpret_reservoir(df: pd.DataFrame) -> pd.DataFrame:
    """Выделяет нефтеносные интервалы (коллекторы)."""
    collectors = df[df['lithology'] == "Нефтеносный песчаник"].copy()
    if collectors.empty:
        return pd.DataFrame()

    collectors['block'] = (collectors['md'].diff() > 1.0).cumsum()
    summary = collectors.groupby('block').agg(
        md_top =('md', 'min'),
        md_base=('md', 'max'),
        avg_gr =('gr', 'mean'),
        avg_res=('res_deep', 'mean'),
    ).reset_index(drop=True)
    summary['thickness_m'] = (summary['md_base'] - summary['md_top']).round(1)
    summary['avg_gr']      = summary['avg_gr'].round(1)
    summary['avg_res']     = summary['avg_res'].round(1)
    return summary


def plot_lwd_log(df: pd.DataFrame, well_name: str = "247Г-Б"):
    """Строит стандартный двухдорожечный LWD-лог."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 10), sharey=True)
    fig.suptitle(f"LWD-лог · Скважина {well_name} · Горизонт Ач3",
                 fontsize=12, fontweight='bold')

    md = df['md']

    # Дорожка 1: ГК
    ax1 = axes[0]
    ax1.plot(df['gr'], md, color='#3C3489', linewidth=0.6, alpha=0.85)
    ax1.axvline(GR_SANDSTONE_MAX, color='green', linestyle='--', linewidth=0.8, alpha=0.7)
    ax1.axvline(GR_SILTSTONE_MAX, color='orange', linestyle='--', linewidth=0.8, alpha=0.7)
    ax1.fill_betweenx(md, df['gr'], GR_SANDSTONE_MAX,
                      where=(df['gr'] < GR_SANDSTONE_MAX),
                      color='#f5c842', alpha=0.35, label='Коллектор')
    ax1.set_xlim(0, 200)
    ax1.set_xlabel("ГК, API")
    ax1.set_ylabel("MD, м")
    ax1.set_title("Гамма-каротаж")
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.2)

    # Дорожка 2: УЭС (лог. шкала)
    ax2 = axes[1]
    ax2.semilogx(df['res_deep'], md, color='#993C1D', linewidth=0.8,
                 label='Глубинное', alpha=0.85)
    ax2.semilogx(df['res_med'],  md, color='#D85A30', linewidth=0.6,
                 linestyle='--', label='Среднее', alpha=0.7)
    ax2.axvline(RES_OIL_MIN, color='green', linestyle='--', linewidth=0.8, alpha=0.7)
    ax2.set_xlim(0.1, 500)
    ax2.set_xlabel("УЭС, Ом·м")
    ax2.set_title("Удельное сопротивление")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.2)

    # Дорожка 3: Литология
    ax3 = axes[2]
    for _, row in df.iterrows():
        color = LITHO_COLORS.get(row['lithology'], '#cccccc')
        ax3.barh(row['md'], 1, height=0.12, color=color, align='center')
    ax3.set_xlim(0, 1)
    ax3.set_xlabel("Литология")
    ax3.set_title("Литологический разрез")
    ax3.set_xticks([])
    patches = [mpatches.Patch(color=c, label=l) for l, c in LITHO_COLORS.items()]
    ax3.legend(handles=patches, fontsize=7, loc='lower left')
    ax3.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig("lwd_log.png", dpi=150, bbox_inches='tight')
    print("LWD-лог сохранён: lwd_log.png")
    plt.show()


if __name__ == "__main__":
    print("=== Анализ LWD-кривых · Скважина 247Г-Б ===\n")

    df = generate_lwd_data()
    print(f"Точек по кривым : {len(df)}")
    print(f"MD диапазон     : {df['md'].min():.0f} – {df['md'].max():.0f} м\n")

    # Распределение литологии
    litho_stats = df['lithology'].value_counts()
    print("Литологический состав:")
    for litho, cnt in litho_stats.items():
        pct = cnt / len(df) * 100
        thickness = cnt * 0.1
        print(f"  {litho:<30} {thickness:>7.1f} м  ({pct:.1f}%)")

    # Коллекторы
    print("\nВыделенные нефтеносные интервалы:")
    reservoirs = interpret_reservoir(df)
    if not reservoirs.empty:
        print(reservoirs.to_string(index=False))
    else:
        print("  Коллекторы не выделены.")

    df.to_csv("lwd_curves.csv", index=False)
    print("\nДанные сохранены: lwd_curves.csv")

    plot_lwd_log(df)
