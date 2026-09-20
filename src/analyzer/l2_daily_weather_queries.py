DELETE_FEATURES = """
    WITH deleted AS (
        DELETE FROM
            analysis.station_daily_weather_feature
            AS feature
        WHERE feature.observed_on
            BETWEEN %s AND %s
          AND (
              %s::bigint IS NULL
              OR feature.station_id = %s
          )
          AND (
              %s::text IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM analysis.weather_station_area
                      AS membership
                  WHERE membership.station_id =
                            feature.station_id
                    AND membership.area_code = %s
              )
          )
        RETURNING 1
    )
    SELECT count(*)
    FROM deleted
"""


INSERT_DAILY_FEATURES = """
    WITH inserted AS (
        INSERT INTO
            analysis.station_daily_weather_feature (
                station_id,
                observed_on,
                calculation_version,
                climate_normal_release_id,

                cumulative_mean_temperature,
                cumulative_max_temperature,
                cumulative_min_temperature,
                cumulative_precipitation,
                cumulative_sunshine_duration,
                cumulative_mean_relative_humidity,
                cumulative_mean_wind_speed,

                valid_mean_temperature_days,
                valid_max_temperature_days,
                valid_min_temperature_days,
                valid_precipitation_days,
                valid_sunshine_duration_days,
                valid_mean_relative_humidity_days,
                valid_mean_wind_speed_days,

                cumulative_mean_temperature_anomaly,
                cumulative_max_temperature_anomaly,
                cumulative_min_temperature_anomaly,
                cumulative_precipitation_anomaly,
                cumulative_sunshine_duration_anomaly,

                valid_mean_temperature_normal_days,
                valid_max_temperature_normal_days,
                valid_min_temperature_normal_days,
                valid_precipitation_normal_days,
                valid_sunshine_duration_normal_days,

                cumulative_rain_days,
                cumulative_precipitation_ge_1mm_days,
                cumulative_precipitation_ge_5mm_days,
                cumulative_precipitation_ge_10mm_days,

                cumulative_max_temperature_ge_30c_days,
                cumulative_max_temperature_ge_35c_days,
                cumulative_min_temperature_ge_25c_days,
                cumulative_min_temperature_lt_0c_days,

                cumulative_sunshine_lt_1h_days,
                cumulative_sunshine_lt_3h_days,

                consecutive_rain_days,
                consecutive_dry_days,
                consecutive_hot_days,
                consecutive_cold_days,
                consecutive_low_sunshine_days,

                source_updated_at
            )
        SELECT
            weather.station_id,
            weather.observed_on,
            %s::smallint,
            normal.climate_normal_release_id,

            COALESCE(
                previous.cumulative_mean_temperature,
                0
            ) + COALESCE(
                weather.mean_temperature,
                0
            ),

            COALESCE(
                previous.cumulative_max_temperature,
                0
            ) + COALESCE(
                weather.max_temperature,
                0
            ),

            COALESCE(
                previous.cumulative_min_temperature,
                0
            ) + COALESCE(
                weather.min_temperature,
                0
            ),

            COALESCE(
                previous.cumulative_precipitation,
                0
            ) + COALESCE(
                weather.precipitation,
                0
            ),

            COALESCE(
                previous.cumulative_sunshine_duration,
                0
            ) + COALESCE(
                weather.sunshine_duration,
                0
            ),

            COALESCE(
                previous.cumulative_mean_relative_humidity,
                0
            ) + COALESCE(
                weather.mean_relative_humidity,
                0
            ),

            COALESCE(
                previous.cumulative_mean_wind_speed,
                0
            ) + COALESCE(
                weather.mean_wind_speed,
                0
            ),

            COALESCE(
                previous.valid_mean_temperature_days,
                0
            ) + (
                weather.mean_temperature IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_max_temperature_days,
                0
            ) + (
                weather.max_temperature IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_min_temperature_days,
                0
            ) + (
                weather.min_temperature IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_precipitation_days,
                0
            ) + (
                weather.precipitation IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_sunshine_duration_days,
                0
            ) + (
                weather.sunshine_duration IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_mean_relative_humidity_days,
                0
            ) + (
                weather.mean_relative_humidity IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_mean_wind_speed_days,
                0
            ) + (
                weather.mean_wind_speed IS NOT NULL
            )::integer,

            COALESCE(
                previous.cumulative_mean_temperature_anomaly,
                0
            ) + CASE
                WHEN weather.mean_temperature IS NOT NULL
                 AND normal.mean_temperature IS NOT NULL
                    THEN weather.mean_temperature
                        - normal.mean_temperature
                ELSE 0
            END,

            COALESCE(
                previous.cumulative_max_temperature_anomaly,
                0
            ) + CASE
                WHEN weather.max_temperature IS NOT NULL
                 AND normal.max_temperature IS NOT NULL
                    THEN weather.max_temperature
                        - normal.max_temperature
                ELSE 0
            END,

            COALESCE(
                previous.cumulative_min_temperature_anomaly,
                0
            ) + CASE
                WHEN weather.min_temperature IS NOT NULL
                 AND normal.min_temperature IS NOT NULL
                    THEN weather.min_temperature
                        - normal.min_temperature
                ELSE 0
            END,

            COALESCE(
                previous.cumulative_precipitation_anomaly,
                0
            ) + CASE
                WHEN weather.precipitation IS NOT NULL
                 AND normal.precipitation IS NOT NULL
                    THEN weather.precipitation
                        - normal.precipitation
                ELSE 0
            END,

            COALESCE(
                previous.cumulative_sunshine_duration_anomaly,
                0
            ) + CASE
                WHEN weather.sunshine_duration IS NOT NULL
                 AND normal.sunshine_duration IS NOT NULL
                    THEN weather.sunshine_duration
                        - normal.sunshine_duration
                ELSE 0
            END,

            COALESCE(
                previous.valid_mean_temperature_normal_days,
                0
            ) + (
                weather.mean_temperature IS NOT NULL
                AND normal.mean_temperature IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_max_temperature_normal_days,
                0
            ) + (
                weather.max_temperature IS NOT NULL
                AND normal.max_temperature IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_min_temperature_normal_days,
                0
            ) + (
                weather.min_temperature IS NOT NULL
                AND normal.min_temperature IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_precipitation_normal_days,
                0
            ) + (
                weather.precipitation IS NOT NULL
                AND normal.precipitation IS NOT NULL
            )::integer,

            COALESCE(
                previous.valid_sunshine_duration_normal_days,
                0
            ) + (
                weather.sunshine_duration IS NOT NULL
                AND normal.sunshine_duration IS NOT NULL
            )::integer,

            COALESCE(
                previous.cumulative_rain_days,
                0
            ) + (
                weather.rain_observed IS TRUE
            )::integer,

            COALESCE(
                previous.cumulative_precipitation_ge_1mm_days,
                0
            ) + COALESCE(
                (
                    weather.precipitation >= 10
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_precipitation_ge_5mm_days,
                0
            ) + COALESCE(
                (
                    weather.precipitation >= 50
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_precipitation_ge_10mm_days,
                0
            ) + COALESCE(
                (
                    weather.precipitation >= 100
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_max_temperature_ge_30c_days,
                0
            ) + COALESCE(
                (
                    weather.max_temperature >= 300
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_max_temperature_ge_35c_days,
                0
            ) + COALESCE(
                (
                    weather.max_temperature >= 350
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_min_temperature_ge_25c_days,
                0
            ) + COALESCE(
                (
                    weather.min_temperature >= 250
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_min_temperature_lt_0c_days,
                0
            ) + COALESCE(
                (
                    weather.min_temperature < 0
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_sunshine_lt_1h_days,
                0
            ) + COALESCE(
                (
                    weather.sunshine_duration < 10
                )::integer,
                0
            ),

            COALESCE(
                previous.cumulative_sunshine_lt_3h_days,
                0
            ) + COALESCE(
                (
                    weather.sunshine_duration < 30
                )::integer,
                0
            ),

            CASE
                WHEN weather.rain_observed IS NULL
                    THEN NULL
                WHEN weather.rain_observed IS FALSE
                    THEN 0
                WHEN previous.observed_on =
                        weather.observed_on - 1
                    THEN COALESCE(
                        previous.consecutive_rain_days,
                        0
                    ) + 1
                ELSE 1
            END,

            CASE
                WHEN weather.rain_observed IS NULL
                    THEN NULL
                WHEN weather.rain_observed IS TRUE
                    THEN 0
                WHEN previous.observed_on =
                        weather.observed_on - 1
                    THEN COALESCE(
                        previous.consecutive_dry_days,
                        0
                    ) + 1
                ELSE 1
            END,

            CASE
                WHEN weather.max_temperature IS NULL
                    THEN NULL
                WHEN weather.max_temperature < 300
                    THEN 0
                WHEN previous.observed_on =
                        weather.observed_on - 1
                    THEN COALESCE(
                        previous.consecutive_hot_days,
                        0
                    ) + 1
                ELSE 1
            END,

            CASE
                WHEN weather.min_temperature IS NULL
                    THEN NULL
                WHEN weather.min_temperature >= 0
                    THEN 0
                WHEN previous.observed_on =
                        weather.observed_on - 1
                    THEN COALESCE(
                        previous.consecutive_cold_days,
                        0
                    ) + 1
                ELSE 1
            END,

            CASE
                WHEN weather.sunshine_duration IS NULL
                    THEN NULL
                WHEN weather.sunshine_duration >= 10
                    THEN 0
                WHEN previous.observed_on =
                        weather.observed_on - 1
                    THEN COALESCE(
                        previous.consecutive_low_sunshine_days,
                        0
                    ) + 1
                ELSE 1
            END,

            GREATEST(
                weather.source_updated_at,
                previous.source_updated_at,
                normal.source_updated_at
            )
        FROM analysis.station_daily_weather AS weather

        LEFT JOIN LATERAL (
            SELECT
                feature.*
            FROM analysis.station_daily_weather_feature
                AS feature
            WHERE feature.station_id =
                    weather.station_id
              AND feature.observed_on <
                    weather.observed_on
            ORDER BY feature.observed_on DESC
            LIMIT 1
        ) AS previous
            ON true

        LEFT JOIN LATERAL (
            SELECT
                release.climate_normal_release_id,
                daily_normal.mean_temperature,
                daily_normal.max_temperature,
                daily_normal.min_temperature,
                daily_normal.precipitation,
                daily_normal.sunshine_duration,
                GREATEST(
                    release.source_updated_at,
                    daily_normal.source_updated_at
                ) AS source_updated_at
            FROM analysis.climate_normal_release
                AS release
            LEFT JOIN
                analysis.station_daily_weather_normal
                AS daily_normal
                ON daily_normal.climate_normal_release_id =
                    release.climate_normal_release_id
               AND daily_normal.station_id =
                    weather.station_id
               AND daily_normal.month =
                    EXTRACT(
                        MONTH FROM weather.observed_on
                    )
               AND daily_normal.day =
                    EXTRACT(
                        DAY FROM weather.observed_on
                    )
            WHERE weather.observed_on
                BETWEEN release.applicable_from
                    AND release.applicable_to
            ORDER BY release.applicable_from DESC
            LIMIT 1
        ) AS normal
            ON true

        WHERE weather.observed_on = %s
          AND (
              %s::bigint IS NULL
              OR weather.station_id = %s
          )
          AND (
              %s::text IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM analysis.weather_station_area
                      AS membership
                  WHERE membership.station_id =
                            weather.station_id
                    AND membership.area_code = %s
              )
          )
        RETURNING 1
    )
    SELECT count(*)
    FROM inserted
"""