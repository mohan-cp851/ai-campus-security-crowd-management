CREATE DATABASE IF NOT EXISTS campus_security;
USE campus_security;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'SECURITY_OFFICER', 'EVENT_COORDINATOR') DEFAULT 'SECURITY_OFFICER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    event_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    venue VARCHAR(255) NOT NULL,
    status ENUM('PLANNED', 'ACTIVE', 'COMPLETED', 'CANCELLED') DEFAULT 'PLANNED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS zones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    zone_name VARCHAR(255) NOT NULL,
    area FLOAT NOT NULL, -- in square meters
    capacity INT NOT NULL,
    warning_threshold FLOAT NOT NULL DEFAULT 70.0, -- percentage (e.g. 70%)
    critical_threshold FLOAT NOT NULL DEFAULT 90.0, -- percentage (e.g. 90%)
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS crowd_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    zone_id INT NOT NULL,
    people_count INT NOT NULL DEFAULT 0,
    density FLOAT NOT NULL DEFAULT 0,
    occupancy FLOAT NOT NULL DEFAULT 0,
    status ENUM('SAFE', 'WARNING', 'CRITICAL') DEFAULT 'SAFE',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    zone_id INT NOT NULL,
    severity ENUM('INFO', 'WARNING', 'CRITICAL') NOT NULL,
    message TEXT NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE CASCADE
);

-- Optional: Initial seed data
INSERT IGNORE INTO users (name, email, password_hash, role) VALUES 
('Admin User', 'admin@campus.edu', '$2b$10$EpN.8gM0/8h.2O5.U8k8z.yW7w1j8e9mXU5P.mYm5Z.eJ.9oR.m', 'ADMIN');

-- Incidents Table (Feature 1: Incident Center)
CREATE TABLE IF NOT EXISTS incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    incident_code VARCHAR(50) UNIQUE NOT NULL,
    event_id INT NOT NULL,
    zone_id INT NOT NULL,
    camera_name VARCHAR(100) DEFAULT NULL,
    type VARCHAR(100) NOT NULL,
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'HIGH',
    status ENUM('OPEN', 'ACKNOWLEDGED', 'IN PROGRESS', 'RESOLVED', 'CLOSED') DEFAULT 'OPEN',
    current_crowd INT DEFAULT 0,
    capacity INT DEFAULT 0,
    occupancy FLOAT DEFAULT 0.0,
    peak_crowd INT DEFAULT 0,
    assigned_user_id INT DEFAULT NULL,
    assigned_officer_name VARCHAR(255) DEFAULT 'Not Assigned',
    description TEXT,
    recommended_action TEXT,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE CASCADE
);

-- Incident Timeline Table
CREATE TABLE IF NOT EXISTS incident_timeline (
    id INT AUTO_INCREMENT PRIMARY KEY,
    incident_id INT NOT NULL,
    message TEXT NOT NULL,
    actor VARCHAR(100) DEFAULT 'System',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);

-- Emergency Sessions Table (Feature 2: Emergency Mode)
CREATE TABLE IF NOT EXISTS emergency_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    activated_by VARCHAR(255) DEFAULT 'Security Admin',
    reason TEXT,
    total_initial_crowd INT DEFAULT 0,
    initial_zone_counts JSON,
    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deactivated_at TIMESTAMP NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Crowd History for Trend & Prediction Analytics (Feature 3: AI Crowd Predictions)
CREATE TABLE IF NOT EXISTS crowd_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    zone_id INT NOT NULL,
    people_count INT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE CASCADE
);

-- Predictions Log Table
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zone_id INT NOT NULL,
    prediction_horizon INT NOT NULL,
    current_count INT NOT NULL,
    predicted_count INT NOT NULL,
    capacity INT NOT NULL,
    predicted_occupancy FLOAT NOT NULL,
    risk_level ENUM('SAFE', 'MODERATE', 'WARNING', 'HIGH', 'CRITICAL') DEFAULT 'SAFE',
    confidence FLOAT DEFAULT 0.0,
    model_method VARCHAR(50) DEFAULT 'Linear Regression Trend',
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE CASCADE
);

