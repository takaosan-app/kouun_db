\set ON_ERROR_STOP on

BEGIN;

-- Viewer専用ロールを未作成の場合だけ作成する
SELECT format('CREATE ROLE %I', :'viewer_user')
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'viewer_user'
)
\gexec

-- 再実行時にも属性とパスワードを現在の設定へ合わせる
SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'viewer_user',
    :'viewer_password'
)
\gexec

-- 誤操作時にも永続データを更新できないようにする
SELECT format(
    'ALTER ROLE %I SET default_transaction_read_only TO on',
    :'viewer_user'
)
\gexec

-- 対象DBへの接続を許可する
SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I',
    :'database_name',
    :'viewer_user'
)
\gexec

-- weather・analysisスキーマは参照だけを許可する
SELECT format(
    'REVOKE ALL ON SCHEMA weather, analysis FROM %I',
    :'viewer_user'
)
\gexec

SELECT format(
    'GRANT USAGE ON SCHEMA weather, analysis TO %I',
    :'viewer_user'
)
\gexec

SELECT format(
    'REVOKE ALL ON ALL TABLES IN SCHEMA weather, analysis FROM %I',
    :'viewer_user'
)
\gexec

SELECT format(
    'GRANT SELECT ON ALL TABLES IN SCHEMA weather, analysis TO %I',
    :'viewer_user'
)
\gexec

-- Viewerはシーケンスを使用しない
SELECT format(
    'REVOKE ALL ON ALL SEQUENCES IN SCHEMA weather, analysis FROM %I',
    :'viewer_user'
)
\gexec

-- 今後作成されるテーブルも参照専用にする
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA weather REVOKE ALL ON TABLES FROM %I',
    CURRENT_USER,
    :'viewer_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA weather GRANT SELECT ON TABLES TO %I',
    CURRENT_USER,
    :'viewer_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA analysis REVOKE ALL ON TABLES FROM %I',
    CURRENT_USER,
    :'viewer_user'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA analysis GRANT SELECT ON TABLES TO %I',
    CURRENT_USER,
    :'viewer_user'
)
\gexec

COMMIT;