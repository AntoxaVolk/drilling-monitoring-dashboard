"""
inclinometry.py
Расчёт траектории скважины методом минимальной кривизны (Minimum Curvature Method).
Стандартный промышленный метод, применяемый во всех MWD/LWD системах.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def minimum_curvature(md1: float, md2: float,
                      inc1: float, inc2: float,
                      az1: float,  az2: float) -> tuple:
    """
    Рассчитывает приращения координат методом минимальной кривизны.

    Параметры:
        md1, md2   : измеренные глубины (м)
        inc1, inc2 : зенитные углы (градусы)
        az1, az2   : азимуты (градусы, истинный север)

    Возвращает:
        (dTVD, dNorth, dEast) — приращения координат в метрах
    """
    dm = md2 - md1
    i1, i2 = np.radians(inc1), np.radians(inc2)
    a1, a2 = np.radians(az1),  np.radians(az2)

    # Угол пространственного искривления (dog-leg angle)
    cos_dl = (np.cos(i2 - i1) -
              np.sin(i1) * np.sin(i2) * (1 - np.cos(a2 - a1)))
    cos_dl = np.clip(cos_dl, -1.0, 1.0)
    dl = np.arccos(cos_dl)

    # Коэффициент сглаживания (ratio factor)
    rf = (2 / dl) * np.tan(dl / 2) if dl > 1e-6 else 1.0

    dTVD   = (dm / 2) * (np.cos(i1) + np.cos(i2)) * rf
    dNorth = (dm / 2) * (np.sin(i1)*np.cos(a1) + np.sin(i2)*np.cos(a2)) * rf
    dEast  = (dm / 2) * (np.sin(i1)*np.sin(a1) + np.sin(i2)*np.sin(a2)) * rf

    # Интенсивность набора кривизны DLS (degrees per 30 m)
    dls = np.degrees(dl) / dm * 30 if dm > 0 else 0.0

    return dTVD, dNorth, dEast, dls


def build_trajectory(survey: pd.DataFrame) -> pd.DataFrame:
    """
    Рассчитывает полную траекторию скважины по таблице замеров инклинометрии.

    Входной DataFrame survey должен содержать колонки:
        md  — измеренная глубина, м
        inc — зенитный угол, градусы
        az  — азимут, градусы

    Возвращает DataFrame с добавленными колонками:
        tvd, north, east, dls
    """
    df = survey.copy().reset_index(drop=True)
    tvd   = np.zeros(len(df))
    north = np.zeros(len(df))
    east  = np.zeros(len(df))
    dls   = np.zeros(len(df))

    for i in range(1, len(df)):
        dt, dn, de, dl = minimum_curvature(
            df.loc[i-1, 'md'],  df.loc[i, 'md'],
            df.loc[i-1, 'inc'], df.loc[i, 'inc'],
            df.loc[i-1, 'az'],  df.loc[i, 'az']
        )
        tvd[i]   = tvd[i-1]   + dt
        north[i] = north[i-1] + dn
        east[i]  = east[i-1]  + de
        dls[i]   = dl

    df['tvd']   = np.round(tvd,   2)
    df['north'] = np.round(north, 2)
    df['east']  = np.round(east,  2)
    df['dls']   = np.round(dls,   3)

    return df


def generate_sample_survey(well_name: str = "247Г-Б") -> pd.DataFrame:
    """Генерирует синтетический план инклинометрии горизонтальной скважины."""
    np.random.seed(42)
    mds, incs, azs = [], [], []

    # Вертикальный участок: 0–500 м
    for md in range(0, 501, 30):
        mds.append(md)
        incs.append(round(md * 0.004 + np.random.uniform(-0.1, 0.1), 2))
        azs.append(round(47.0 + np.random.uniform(-0.5, 0.5), 2))

    # Участок набора зенитного угла: 500–1700 м
    for md in range(530, 1701, 30):
        inc = 2 + (md - 500) * 0.073 + np.random.uniform(-0.3, 0.3)
        mds.append(md)
        incs.append(round(min(90.0, inc), 2))
        azs.append(round(47.0 + np.random.uniform(-1.0, 1.0), 2))

    # Горизонтальный участок: 1700–3250 м
    for md in range(1730, 3251, 30):
        mds.append(md)
        incs.append(round(89.5 + np.random.uniform(-0.8, 0.8), 2))
        azs.append(round(47.0 + np.random.uniform(-2.0, 2.0), 2))

    survey = pd.DataFrame({'md': mds, 'inc': incs, 'az': azs})
    return build_trajectory(survey)


def plot_trajectory(df: pd.DataFrame, well_name: str = "Скважина 247Г-Б"):
    """Строит вертикальную и плановую проекции траектории скважины."""
    fig = plt.figure(figsize=(14, 6))
    fig.suptitle(f"Траектория скважины: {well_name}", fontsize=13, fontweight='bold')
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.35)

    # Вертикальная проекция
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df['north'], df['tvd'], color='#1a5fa8', linewidth=2, label='Траектория')
    ax1.scatter(df['north'].iloc[-1], df['tvd'].iloc[-1],
                color='#e05c00', s=60, zorder=5, label=f"Забой: MD {df['md'].iloc[-1]:.0f} м")
    ax1.invert_yaxis()
    ax1.set_xlabel("Горизонт. отход (север), м")
    ax1.set_ylabel("TVD, м")
    ax1.set_title("Вертикальная проекция")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Плановая проекция
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(df['east'], df['north'], color='#1a8a5f', linewidth=2, label='Траектория')
    ax2.scatter(0, 0, color='#333', s=80, zorder=5, marker='^', label='Устье')
    ax2.scatter(df['east'].iloc[-1], df['north'].iloc[-1],
                color='#e05c00', s=60, zorder=5, label='Забой')
    ax2.set_xlabel("Восток, м")
    ax2.set_ylabel("Север, м")
    ax2.set_title("Плановая проекция (вид сверху)")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')

    plt.savefig("trajectory_plot.png", dpi=150, bbox_inches='tight')
    print("График сохранён: trajectory_plot.png")
    plt.show()


if __name__ == "__main__":
    print("=== Расчёт траектории скважины 247Г-Б ===\n")
    df = generate_sample_survey()

    print("Сводка по траектории:")
    print(f"  Замеров инклинометрии : {len(df)}")
    print(f"  Максимальная MD       : {df['md'].max():.0f} м")
    print(f"  Максимальная TVD      : {df['tvd'].max():.1f} м")
    print(f"  Макс. зенитный угол   : {df['inc'].max():.1f}°")
    print(f"  Горизонт. отход (N)   : {df['north'].iloc[-1]:.1f} м")
    print(f"  Горизонт. отход (E)   : {df['east'].iloc[-1]:.1f} м")
    print(f"  Макс. DLS             : {df['dls'].max():.2f} °/30м\n")

    print("Таблица (первые и последние 5 строк):")
    display_cols = ['md', 'inc', 'az', 'tvd', 'north', 'east', 'dls']
    print(pd.concat([df[display_cols].head(5), df[display_cols].tail(5)]).to_string(index=False))

    df.to_csv("inclinometry_output.csv", index=False)
    print("\nДанные сохранены: inclinometry_output.csv")

    plot_trajectory(df)
