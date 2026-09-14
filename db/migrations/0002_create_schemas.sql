\set ON_ERROR_STOP on

BEGIN;

CREATE SCHEMA IF NOT EXISTS weather;
CREATE SCHEMA IF NOT EXISTS analysis;

REVOKE ALL ON SCHEMA weather FROM PUBLIC;
REVOKE ALL ON SCHEMA analysis FROM PUBLIC;

-- collectorは観測データ領域を利用する
SELECT format(
    'GRANT USAGE ON SCHEMA weather TO %I',
    :'collector_user'
)
\gexec

-- analyzerは観測データを読み、分析領域を利用する
SELECT format(
    'GRANT USAGE ON SCHEMA weather TO %I',
    :'analyzer_user'
)
\gexec

SELECT format(
    'GRANT USAGE ON SCHEMA analysis TO %I',
    :'analyzer_user'
)
\gexec

-- 既存テーブルへの権限
SELECT format(
    'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA weather TO %I',
    :'collector_user'
)
\gexec

SELECT format(
    'GRANT SELECT ON ALL TABLES IN SCHEMA weather TO %I',
    :'analyzer_user'
)
\gexec

SELECT format(
    'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analysis TO %I',
    :'analyzer_user'
)
\gexec

-- 今後管理者が作成するテーブルにも同じ権限を適用する
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA weather GRANT SELECT, INSERT, UPDATE ON TABLES TO %I',
    CURRENT_USER,
    :'collector_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA weather GRANT SELECT ON TABLES TO %I',
    CURRENT_USER,
    :'analyzer_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA analysis GRANT SELECT, INSERT, UPDATE ON TABLES TO %I',
    CURRENT_USER,
    :'analyzer_user'
)
\gexec

-- ID列などで使用するシーケンスの権限
SELECT format(
    'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA weather TO %I',
    :'collector_user'
)
\gexec

SELECT format(
    'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analysis TO %I',
    :'analyzer_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA weather GRANT USAGE, SELECT ON SEQUENCES TO %I',
    CURRENT_USER,
    :'collector_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA analysis GRANT USAGE, SELECT ON SEQUENCES TO %I',
    CURRENT_USER,
    :'analyzer_user'
)
\gexec

COMMIT;