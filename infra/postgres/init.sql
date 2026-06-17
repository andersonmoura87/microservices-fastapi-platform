-- Bootstrap the per-service schemas on a shared PostgreSQL instance.
-- Each service owns exactly one schema and never reaches across the boundary.
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS data;
