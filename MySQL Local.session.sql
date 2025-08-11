CREATE DATABASE IF NOT EXISTS homimeet_db;
USE homimeet_db;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- Groups Table
CREATE TABLE IF NOT EXISTS groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Group Members (many-to-many)
CREATE TABLE IF NOT EXISTS group_members (
    group_id INT,
    user_id INT,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Meetups Table
CREATE TABLE IF NOT EXISTS meetups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT,
    location VARCHAR(255),
    scheduled_time DATETIME,
    status ENUM('scheduled', 'canceled', 'rescheduled') DEFAULT 'scheduled',
    created_by INT,
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Punctuality Logs
CREATE TABLE IF NOT EXISTS punctuality_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    meetup_id INT,
    status ENUM('on_time', 'late', 'absent'),
    score INT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (meetup_id) REFERENCES meetups(id)
);

-- Add a table to store invitations
CREATE TABLE IF NOT EXISTS invitations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    meetup_id INT,
    status ENUM('pending', 'accepted', 'declined') DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (meetup_id) REFERENCES meetups(id)
);

-- Add a table for profile customization (bio)
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INT PRIMARY KEY,
    bio TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

SHOW TABLES;
SELECT username, password FROM users;