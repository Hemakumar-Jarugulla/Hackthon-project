-- ============================================================================
-- AttributionIQ - MySQL 8+ / 9+ Database Initialization Script
-- Run from the repository root as a privileged MySQL user (e.g., root).
-- PowerShell:
--   Get-Content -Raw .\database\init_mysql.sql | & 'C:\Program Files\MySQL\MySQL Server 9.1\bin\mysql.exe' -u root -p
-- Command Prompt:
--   "C:\Program Files\MySQL\MySQL Server 9.1\bin\mysql.exe" -u root -p < database\init_mysql.sql
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `attribution_iq`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `attribution_iq`;

-- Optional dedicated least-privilege application account for local/production use.
-- Update the password before uncommenting in non-local environments.
-- CREATE USER IF NOT EXISTS 'attribution_user'@'localhost' IDENTIFIED BY 'ChangeMeStrongPassword!2026';
-- GRANT ALL PRIVILEGES ON `attribution_iq`.* TO 'attribution_user'@'localhost';
-- FLUSH PRIVILEGES;

SELECT
  DATABASE() AS active_database,
  @@version AS mysql_version,
  @@character_set_database AS charset,
  @@collation_database AS collation,
  @@sql_mode AS sql_mode;
