\set ON_ERROR_STOP on

BEGIN;

-- ロールが存在しない場合だけ作成する
SELECT format('CREATE ROLE %I', :'collector_user')
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'collector_user'
)
\gexec

SELECT format('CREATE ROLE %I', :'analyzer_user')
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'analyzer_user'
)
\gexec

-- 再実行時には属性とパスワードを現在の設定へ合わせる
SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'collector_user',
    :'collector_password'
)
\gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'analyzer_user',
    :'analyzer_password'
)
\gexec

-- 対象DBへの接続を明示したロールだけに許可する
SELECT format(
    'REVOKE CONNECT ON DATABASE %I FROM PUBLIC',
    :'database_name'
)
\gexec

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I',
    :'database_name',
    :'collector_user'
)
\gexec

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I',
    :'database_name',
    :'analyzer_user'
)
\gexec

COMMIT;
