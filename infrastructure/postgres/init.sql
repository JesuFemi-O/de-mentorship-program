CREATE SCHEMA IF NOT EXISTS inventory;

CREATE TABLE inventory.customers (
  id          SERIAL PRIMARY KEY,
  first_name  VARCHAR(255) NOT NULL,
  last_name   VARCHAR(255) NOT NULL,
  email       VARCHAR(255) UNIQUE NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO inventory.customers (first_name, last_name, email) VALUES
  ('Sally',  'Thomas',    'sally.thomas@example.com'),
  ('George', 'Bailey',    'gbailey@example.com'),
  ('Edward', 'Walker',    'ed@example.com'),
  ('Anne',   'Kretchmar', 'annek@example.com');

ALTER TABLE inventory.customers REPLICA IDENTITY FULL;
