-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS USER (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE INDEX idx_username (username),
    UNIQUE INDEX idx_email (email),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de historial de descargas
CREATE TABLE IF NOT EXISTS DOWNLOAD_HISTORY (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    url VARCHAR(2048) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'failed') NOT NULL,
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES USER(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_download_date (download_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Procedimiento para registrar una descarga
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS register_download(
    IN p_user_id INT,
    IN p_url VARCHAR(2048),
    IN p_filename VARCHAR(255),
    IN p_status VARCHAR(10),
    IN p_error_message TEXT
)
BEGIN
    INSERT INTO DOWNLOAD_HISTORY (user_id, url, filename, status, error_message)
    VALUES (p_user_id, p_url, p_filename, p_status, p_error_message);
    
    UPDATE USER 
    SET last_login = CURRENT_TIMESTAMP 
    WHERE id = p_user_id;
END //
DELIMITER ;
