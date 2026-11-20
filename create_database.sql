CREATE DATABASE IF NOT EXISTS jobs_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'jobs_user'@'localhost' IDENTIFIED BY 'ChangeMe_123!';
GRANT ALL PRIVILEGES ON jobs_db.* TO 'jobs_user'@'localhost';
FLUSH PRIVILEGES;