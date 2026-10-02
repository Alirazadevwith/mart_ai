#!/usr/bin/env bash
# Creates (or repairs) the local PostgreSQL role and databases for Mart AI.
# Safe to re-run. Requires sudo access to the `postgres` superuser.
#
#   bash backend/scripts/setup_db.sh
set -euo pipefail

DB_USER="${POSTGRES_USER:-mart_ai}"
DB_PASS="${POSTGRES_PASSWORD:-mart_ai_dev_pw}"
DB_MAIN="${POSTGRES_DB:-mart_ai}"
DB_TEST="${POSTGRES_TEST_DB:-mart_ai_test}"

su_psql() { sudo -u postgres psql -v ON_ERROR_STOP=1 "$@"; }

echo "==> Ensuring role '${DB_USER}' exists with the expected password"
su_psql -c "DO \$\$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    ALTER ROLE ${DB_USER} WITH LOGIN CREATEDB PASSWORD '${DB_PASS}';
    RAISE NOTICE 'role ${DB_USER} updated';
  ELSE
    CREATE ROLE ${DB_USER} WITH LOGIN CREATEDB PASSWORD '${DB_PASS}';
    RAISE NOTICE 'role ${DB_USER} created';
  END IF;
END
\$\$;"

for db in "${DB_MAIN}" "${DB_TEST}"; do
  if [ "$(su_psql -tAc "SELECT 1 FROM pg_database WHERE datname = '${db}'")" = "1" ]; then
    echo "==> Database '${db}' already exists; reassigning owner to ${DB_USER}"
    su_psql -c "ALTER DATABASE ${db} OWNER TO ${DB_USER};"
  else
    echo "==> Creating database '${db}'"
    su_psql -c "CREATE DATABASE ${db} OWNER ${DB_USER};"
  fi
  su_psql -d "${db}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"
done

echo "==> Verifying login"
PGPASSWORD="${DB_PASS}" psql -h localhost -U "${DB_USER}" -d "${DB_MAIN}" \
  -c "SELECT current_database() AS database, current_user AS role;"

echo "==> Done."
