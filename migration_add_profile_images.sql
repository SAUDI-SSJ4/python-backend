-- Migration to add profile_image fields and update password column names
-- Update database to add profile image fields only
-- Note: academies table already has logo and cover columns

-- Update students table
ALTER TABLE students 
CHANGE COLUMN password hashed_password VARCHAR(255) NOT NULL,
CHANGE COLUMN avatar profile_image VARCHAR(255) NULL;

-- Update academy_users table (add profile_image only)
ALTER TABLE academy_users 
CHANGE COLUMN password hashed_password VARCHAR(255) NOT NULL,
ADD COLUMN profile_image VARCHAR(255) NULL AFTER hashed_password;

-- Update admins table
ALTER TABLE admins 
CHANGE COLUMN password hashed_password VARCHAR(255) NOT NULL,
ADD COLUMN profile_image VARCHAR(255) NULL AFTER hashed_password;

-- Note: academies table already has logo and cover columns 