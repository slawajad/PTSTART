CREATE TABLE IF NOT EXISTS email_addresses(
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS phone_numbers(
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) NOT NULL
);

INSERT INTO phone_numbers( phone_number) VALUES('88001234567');
INSERT INTO phone_numbers( phone_number) VALUES('77007775555');
INSERT INTO phone_numbers( phone_number) VALUES('86001230003');

INSERT INTO email_addresses(email) VALUES('info@example.com');
INSERT INTO email_addresses(email) VALUES('contact@site.org');
INSERT INTO email_addresses(email) VALUES('support@web.net');