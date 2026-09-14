\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE weather.element_source_id
    DROP CONSTRAINT element_source_id_unique;

ALTER TABLE weather.element_source_id
    ADD CONSTRAINT element_source_id_unique
    UNIQUE (
        source_id,
        element_id,
        source_element_code,
        source_element_option
    );

INSERT INTO weather.element (
    element_key,
    name,
    unit,
    aggregation,
    value_kind
)
VALUES
    (
        'daily_sunshine_duration',
        '日照時間',
        'h',
        'sum',
        'numeric'
    ),
    (
        'daily_mean_station_pressure',
        '日平均現地気圧',
        'hPa',
        'mean',
        'numeric'
    ),
    (
        'daily_mean_sea_level_pressure',
        '日平均海面気圧',
        'hPa',
        'mean',
        'numeric'
    ),
    (
        'daily_mean_relative_humidity',
        '日平均相対湿度',
        'percent',
        'mean',
        'numeric'
    ),
    (
        'daily_min_relative_humidity',
        '日最小相対湿度',
        'percent',
        'minimum',
        'numeric'
    ),
    (
        'daily_mean_wind_speed',
        '日平均風速',
        'm/s',
        'mean',
        'numeric'
    ),
    (
        'daily_max_wind_speed',
        '日最大風速',
        'm/s',
        'maximum',
        'numeric'
    ),
    (
        'daily_max_wind_direction',
        '日最大風速時風向',
        'direction',
        'direction_at_maximum',
        'direction'
    ),
    (
        'daily_max_instantaneous_wind_speed',
        '日最大瞬間風速',
        'm/s',
        'maximum',
        'numeric'
    ),
    (
        'daily_max_instantaneous_wind_direction',
        '日最大瞬間風速時風向',
        'direction',
        'direction_at_maximum',
        'direction'
    ),
    (
        'daily_most_frequent_wind_direction',
        '日最多風向',
        'direction',
        'mode',
        'direction'
    ),
    (
        'daily_max_snow_depth',
        '日最深積雪',
        'cm',
        'maximum',
        'numeric'
    ),
    (
        'daily_snowfall',
        '日降雪量合計',
        'cm',
        'sum',
        'numeric'
    ),
    (
        'daily_weather_summary_daytime',
        '昼間天気概況',
        'text',
        'summary',
        'text'
    ),
    (
        'daily_weather_summary_nighttime',
        '夜間天気概況',
        'text',
        'summary',
        'text'
    )
ON CONFLICT (element_key) DO UPDATE
SET
    name = EXCLUDED.name,
    unit = EXCLUDED.unit,
    aggregation = EXCLUDED.aggregation,
    value_kind = EXCLUDED.value_kind;

INSERT INTO weather.element_source_id (
    source_id,
    element_id,
    source_element_code,
    source_element_option
)
SELECT
    source.id,
    element.id,
    mapping.source_element_code,
    ''
FROM weather.source
JOIN (
    VALUES
        ('daily_sunshine_duration', '401'),
        ('daily_mean_station_pressure', '601'),
        ('daily_mean_sea_level_pressure', '602'),
        ('daily_mean_relative_humidity', '605'),
        ('daily_min_relative_humidity', '606'),
        ('daily_mean_wind_speed', '301'),
        ('daily_max_wind_speed', '302'),
        ('daily_max_wind_direction', '302'),
        ('daily_max_instantaneous_wind_speed', '304'),
        ('daily_max_instantaneous_wind_direction', '304'),
        ('daily_most_frequent_wind_direction', '305'),
        ('daily_max_snow_depth', '501'),
        ('daily_snowfall', '503'),
        ('daily_weather_summary_daytime', '701'),
        ('daily_weather_summary_nighttime', '702')
) AS mapping(element_key, source_element_code)
    ON true
JOIN weather.element
    ON element.element_key = mapping.element_key
WHERE source.source_key = 'jma_obsdl'
ON CONFLICT (
    source_id,
    element_id,
    source_element_code,
    source_element_option
) DO NOTHING;

COMMIT;