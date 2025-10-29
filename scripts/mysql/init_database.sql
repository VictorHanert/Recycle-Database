-- ============================================
-- DATABASE INITIALIZATION SCRIPT
-- Creates stored procedures, functions, views, triggers, events
-- Run automatically on application startup
-- ============================================

USE marketplace;

-- ============================================
-- STORED PROCEDURES
-- ============================================

DELIMITER $$

-- Get user's products with statistics
DROP PROCEDURE IF EXISTS GetUserProducts$$
CREATE PROCEDURE GetUserProducts(IN user_id INT)
BEGIN
    SELECT 
        p.id,
        p.title,
        p.price_amount as price,
        p.status,
        p.created_at,
        c.name AS category_name,
        COUNT(DISTINCT CONCAT(f.user_id, '-', f.product_id)) AS favorite_count,
        COUNT(DISTINCT iv.id) AS view_count
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    LEFT JOIN favorites f ON p.id = f.product_id
    LEFT JOIN item_views iv ON p.id = iv.product_id
    WHERE p.seller_id = user_id
    GROUP BY p.id, p.title, p.price_amount, p.status, p.created_at, c.name
    ORDER BY p.created_at DESC;
END$$

-- Archive sold product with transaction
DROP PROCEDURE IF EXISTS ArchiveSoldProduct$$
CREATE PROCEDURE ArchiveSoldProduct(
    IN p_product_id INT,
    IN p_buyer_id INT,
    IN p_sale_price DECIMAL(10,2)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error archiving product';
    END;
    
    START TRANSACTION;
    
    -- Insert into sold archive
    INSERT INTO sold_item_archive (
        product_id, title, category_id, location_id,
        price_amount, price_currency, sold_at
    )
    SELECT 
        id, title, category_id, location_id,
        price_amount, price_currency, NOW()
    FROM products
    WHERE id = p_product_id;
    
    -- Update product status
    UPDATE products 
    SET status = 'sold',
        updated_at = NOW()
    WHERE id = p_product_id;
    
    COMMIT;
END$$

-- Get product recommendations based on category and tags
DROP PROCEDURE IF EXISTS GetProductRecommendations$$
CREATE PROCEDURE GetProductRecommendations(
    IN p_product_id INT,
    IN p_limit INT
)
BEGIN
    SELECT DISTINCT
        p.id,
        p.title,
        p.price_amount as price,
        p.status,
        p.created_at,
        (
            -- Score based on shared tags
            (SELECT COUNT(*) 
             FROM product_tags pt1 
             JOIN product_tags pt2 ON pt1.tag_id = pt2.tag_id
             WHERE pt1.product_id = p_product_id 
             AND pt2.product_id = p.id) * 3
            +
            -- Score based on same category
            IF(p.category_id = (SELECT category_id FROM products WHERE id = p_product_id), 2, 0)
        ) AS relevance_score
    FROM products p
    WHERE p.id != p_product_id
    AND p.status = 'active'
    HAVING relevance_score > 0
    ORDER BY relevance_score DESC, p.created_at DESC
    LIMIT p_limit;
END$$

DELIMITER ;

-- ============================================
-- STORED FUNCTIONS
-- ============================================

DELIMITER $$

-- Get product age in days
DROP FUNCTION IF EXISTS GetProductAgeDays$$
CREATE FUNCTION GetProductAgeDays(p_product_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE age_days INT;
    
    SELECT DATEDIFF(NOW(), created_at) INTO age_days
    FROM products
    WHERE id = p_product_id;
    
    RETURN COALESCE(age_days, 0);
END$$

DELIMITER ;

-- ============================================
-- VIEWS
-- ============================================

-- Popular products by favorites and views
DROP VIEW IF EXISTS vw_popular_products;
CREATE VIEW vw_popular_products AS
SELECT 
    p.id,
    p.title,
    p.price_amount,
    p.status,
    COUNT(DISTINCT f.id) AS favorite_count,
    COUNT(DISTINCT iv.id) AS view_count,
    (COUNT(DISTINCT f.id) * 2 + COUNT(DISTINCT iv.id)) AS popularity_score
FROM products p
LEFT JOIN favorites f ON p.id = f.product_id
LEFT JOIN item_views iv ON p.id = iv.product_id
WHERE p.status = 'active'
GROUP BY p.id, p.title, p.price_amount, p.status
HAVING popularity_score > 0
ORDER BY popularity_score DESC;

-- ============================================
-- AUDIT TABLE & TRIGGERS
-- ============================================

-- Audit: A table that keeps a history of all changes made to important data and storing what was changed.
-- Triggers: Automatic actions that run when data is updated or deleted, so we can log changes into the audit table.

-- Create audit table for product changes
CREATE TABLE IF NOT EXISTS product_audit (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    action_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    old_title VARCHAR(255),
    new_title VARCHAR(255),
    changed_by INT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_id (product_id),
    INDEX idx_changed_at (changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Trigger: After product insert
DROP TRIGGER IF EXISTS trg_product_after_insert;
DELIMITER $$
CREATE TRIGGER trg_product_after_insert
AFTER INSERT ON products
FOR EACH ROW
BEGIN
    INSERT INTO product_audit (
        product_id, action_type, new_price, new_status, new_title, changed_by
    )
    VALUES (
        NEW.id, 'INSERT', NEW.price_amount, NEW.status, NEW.title, NEW.seller_id
    );
END$$
DELIMITER ;

-- Trigger: After product update
DROP TRIGGER IF EXISTS trg_product_after_update;
DELIMITER $$
CREATE TRIGGER trg_product_after_update
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    INSERT INTO product_audit (
        product_id, action_type,
        old_price, new_price,
        old_status, new_status,
        old_title, new_title,
        changed_by
    )
    VALUES (
        NEW.id, 'UPDATE',
        OLD.price_amount, NEW.price_amount,
        OLD.status, NEW.status,
        OLD.title, NEW.title,
        NEW.seller_id
    );
END$$
DELIMITER ;

-- Trigger: Before product delete (audit before deletion)
DROP TRIGGER IF EXISTS trg_product_before_delete;
DELIMITER $$
CREATE TRIGGER trg_product_before_delete
BEFORE DELETE ON products
FOR EACH ROW
BEGIN
    INSERT INTO product_audit (
        product_id, action_type, old_price, old_status, old_title, changed_by
    )
    VALUES (
        OLD.id, 'DELETE', OLD.price_amount, OLD.status, OLD.title, OLD.seller_id
    );
END$$
DELIMITER ;

-- ============================================
-- EVENTS (Scheduled Tasks)
-- ============================================

-- Enable event scheduler
SET GLOBAL event_scheduler = ON;

-- Event: Mark old inactive products as expired (runs daily at 2 AM)
DROP EVENT IF EXISTS evt_expire_old_products;
DELIMITER $$
CREATE EVENT evt_expire_old_products
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    UPDATE products
    SET status = 'expired',
        updated_at = NOW()
    WHERE status = 'active'
    AND DATEDIFF(NOW(), created_at) > 100  -- 100 days old
    AND id NOT IN (
        SELECT DISTINCT product_id 
        FROM item_views 
        WHERE viewed_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
    );
END$$
DELIMITER ;

-- ============================================
-- FULL-TEXT SEARCH INDEX
-- ============================================

-- Check if full-text index exists, if not create it
SET @index_exists = (
    SELECT COUNT(*) 
    FROM information_schema.statistics 
    WHERE table_schema = DATABASE() 
    AND table_name = 'products' 
    AND index_name = 'ft_product_search'
);

SET @sql = IF(@index_exists = 0,
    'ALTER TABLE products ADD FULLTEXT INDEX ft_product_search (title, description)',
    'SELECT "Full-text index already exists" AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================
-- COMPLETION MESSAGE
-- ============================================
SELECT 'Database stored objects initialized successfully!' AS message;
