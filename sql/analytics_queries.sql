-- =============================================================
-- analytics_queries.sql  ·  Аналитические запросы по бурению
-- =============================================================

-- ── 1. Средний РОП по интервалам 100 м ─────────────────────────────────────
SELECT
    FLOOR(md / 100) * 100          AS md_interval,
    ROUND(AVG(rop)::numeric, 2)    AS avg_rop_mh,
    ROUND(AVG(wob)::numeric, 2)    AS avg_wob_t,
    ROUND(AVG(rpm)::numeric, 0)    AS avg_rpm,
    COUNT(*)                        AS records
FROM drilling_params
WHERE well_id = 247
  AND rop > 0
GROUP BY md_interval
ORDER BY md_interval;


-- ── 2. НПВ по суткам ────────────────────────────────────────────────────────
SELECT
    DATE_TRUNC('day', ts_utc)              AS day,
    SUM(CASE WHEN rop = 0 THEN 1 ELSE 0 END)          AS npt_minutes,
    COUNT(*)                                            AS total_minutes,
    ROUND(
        100.0 * SUM(CASE WHEN rop = 0 THEN 1 ELSE 0 END) / COUNT(*),
        1
    )                                                   AS npt_pct,
    ROUND(AVG(CASE WHEN rop > 0 THEN rop END)::numeric, 2) AS avg_rop_active
FROM drilling_params
WHERE well_id = 247
GROUP BY day
ORDER BY day;


-- ── 3. Детекция аномалий давления (признак ГНВП) ────────────────────────────
WITH pressure_diff AS (
    SELECT
        ts_utc, md, spp,
        LAG(spp, 5) OVER (PARTITION BY well_id ORDER BY ts_utc) AS spp_5min_ago
    FROM drilling_params
    WHERE well_id = 247
)
SELECT
    ts_utc,
    md,
    spp,
    spp_5min_ago,
    ROUND((spp - spp_5min_ago)::numeric, 1) AS delta_spp_bar,
    'ГНВП-риск: рост СПП'                   AS alert
FROM pressure_diff
WHERE spp - spp_5min_ago > 20
ORDER BY ts_utc;


-- ── 4. Литологическая разбивка по ГК ────────────────────────────────────────
SELECT
    md,
    gr,
    res_deep,
    CASE
        WHEN gr < 45 AND res_deep >= 15 THEN 'Нефтеносный песчаник'
        WHEN gr < 45                    THEN 'Водонасыщенный песчаник'
        WHEN gr < 75                    THEN 'Алевролит'
        ELSE                                 'Аргиллит/глина'
    END AS lithology
FROM lwd_curves
WHERE well_id = 247
ORDER BY md;


-- ── 5. Суммарная мощность коллекторов ───────────────────────────────────────
SELECT
    CASE
        WHEN gr < 45 AND res_deep >= 15 THEN 'Нефтеносный песчаник'
        WHEN gr < 45                    THEN 'Водонасыщенный песчаник'
        WHEN gr < 75                    THEN 'Алевролит'
        ELSE                                 'Аргиллит/глина'
    END                                     AS lithology,
    COUNT(*)          * 0.1                 AS thickness_m,   -- шаг 0.1 м
    ROUND(AVG(gr)::numeric, 1)              AS avg_gr_api,
    ROUND(AVG(res_deep)::numeric, 1)        AS avg_res_ohmm
FROM lwd_curves
WHERE well_id = 247
  AND md BETWEEN 2847 AND 3250
GROUP BY lithology
ORDER BY thickness_m DESC;


-- ── 6. Интенсивность набора кривизны (DLS) > 3°/30м (потенциальный прихват) ─
SELECT
    i.md,
    i.inclination,
    i.azimuth,
    i.dls,
    'DLS > 3°/30м — риск прихвата' AS warning
FROM inclinometry i
WHERE i.well_id = 247
  AND i.dls > 3.0
ORDER BY i.md;


-- ── 7. Скользящий средний РОП (6-часовое окно) ──────────────────────────────
SELECT
    ts_utc,
    md,
    rop,
    ROUND(
        AVG(rop) OVER (
            PARTITION BY well_id
            ORDER BY ts_utc
            ROWS BETWEEN 360 PRECEDING AND CURRENT ROW
        )::numeric, 2
    ) AS rop_6h_avg
FROM drilling_params
WHERE well_id = 247
  AND rop > 0
ORDER BY ts_utc;
