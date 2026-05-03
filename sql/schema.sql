-- =============================================================
-- schema.sql  ·  Drilling Monitoring Database (PostgreSQL 15)
-- =============================================================

-- Скважины
CREATE TABLE IF NOT EXISTS wells (
    well_id     SERIAL PRIMARY KEY,
    well_name   VARCHAR(50)  NOT NULL,
    field_name  VARCHAR(100),
    cluster_no  INT,
    well_type   VARCHAR(20)  CHECK (well_type IN ('Горизонтальная','ННС','Вертикальная')),
    spud_date   DATE,
    td_planned  FLOAT,                        -- проектная глубина, м
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Инклинометрия
CREATE TABLE IF NOT EXISTS inclinometry (
    id          SERIAL PRIMARY KEY,
    well_id     INT REFERENCES wells(well_id) ON DELETE CASCADE,
    md          FLOAT NOT NULL,               -- измеренная глубина, м
    inclination FLOAT NOT NULL,               -- зенитный угол, °
    azimuth     FLOAT NOT NULL,               -- азимут, °
    tvd         FLOAT,                        -- вертикальная глубина, м
    northing    FLOAT,                        -- смещение на север, м
    easting     FLOAT,                        -- смещение на восток, м
    dls         FLOAT,                        -- интенсивность набора, °/30м
    ts_utc      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incl_well_md ON inclinometry (well_id, md);

-- Параметры бурения (1 запись в минуту)
CREATE TABLE IF NOT EXISTS drilling_params (
    id          SERIAL PRIMARY KEY,
    well_id     INT REFERENCES wells(well_id) ON DELETE CASCADE,
    ts_utc      TIMESTAMPTZ NOT NULL,
    md          FLOAT,                        -- измеренная глубина, м
    rop         FLOAT,                        -- механическая скорость, м/ч
    wob         FLOAT,                        -- нагрузка на долото, тс
    rpm         INT,                          -- обороты, об/мин
    torque      FLOAT,                        -- момент на роторе, кН·м
    flow_rate   FLOAT,                        -- расход промывочной жидкости, л/с
    spp         FLOAT                         -- давление СПП, бар
);

CREATE INDEX IF NOT EXISTS idx_dp_well_ts ON drilling_params (well_id, ts_utc);

-- LWD-кривые
CREATE TABLE IF NOT EXISTS lwd_curves (
    id          SERIAL PRIMARY KEY,
    well_id     INT REFERENCES wells(well_id) ON DELETE CASCADE,
    md          FLOAT NOT NULL,
    gr          FLOAT,                        -- гамма-каротаж, API
    res_deep    FLOAT,                        -- УЭС глубинное, Ом·м
    res_med     FLOAT,                        -- УЭС среднее, Ом·м
    res_sh      FLOAT,                        -- УЭС мелкое, Ом·м
    lithology   VARCHAR(50)                   -- автоматическая классификация
);

CREATE INDEX IF NOT EXISTS idx_lwd_well_md ON lwd_curves (well_id, md);

-- Журнал событий и аномалий
CREATE TABLE IF NOT EXISTS events_log (
    id          SERIAL PRIMARY KEY,
    well_id     INT REFERENCES wells(well_id) ON DELETE CASCADE,
    ts_utc      TIMESTAMPTZ NOT NULL,
    md          FLOAT,
    event_type  VARCHAR(30) CHECK (event_type IN ('ГНВП-риск','НПВ','Поглощение','Прихват','Информация','Предупреждение')),
    description TEXT,
    resolved_at TIMESTAMPTZ
);
