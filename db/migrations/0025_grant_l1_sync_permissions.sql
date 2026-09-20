\set ON_ERROR_STOP on

BEGIN;

SELECT format(
    'GRANT DELETE ON TABLE '
    'analysis.weather_station_area, '
    'analysis.station_element_capability '
    'TO %I',
    :'analyzer_user'
)
\gexec

COMMIT;
