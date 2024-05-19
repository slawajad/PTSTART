CREATE DATABASE  DB_DATABASE;
CREATE USER DB_USER WITH REPLICATION ENCRYPTED PASSWORD 'DB_PASSWORD';
CREATE USER DB_REPL_USER  WITH REPLICATION ENCRYPTED PASSWORD 'DB_REPL_PASSWORD';
SELECT pg_create_physical_replication_slot('replication_slot');
GRANT pg_read_all_data TO DB_REPL_USER ; GRANT pg_write_all_data TO DB_REPL_USER;

\connect DB_DATABASE

CREATE TABLE IF NOT EXISTS email_addresses(
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS phone_numbers(
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) NOT NULL
);
INSERT INTO phone_numbers( phone_number) VALUES('8 (800) 123-45-67');
INSERT INTO phone_numbers( phone_number) VALUES('+7 (700) 777-55-55');
INSERT INTO phone_numbers( phone_number) VALUES('8 (600) 123-00-03');

INSERT INTO email_addresses(email) VALUES('info@example.com');
INSERT INTO email_addresses(email) VALUES('contact@site.org');
INSERT INTO email_addresses(email) VALUES('support@web.net');

