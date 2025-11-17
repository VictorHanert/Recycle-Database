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

    -- Insert into sold archive with buyer and sale price
    INSERT INTO sold_item_archive (
        product_id, buyer_id, title, category_id, location_id,
        price_amount, price_currency, sold_at
    )
    SELECT
        id, p_buyer_id, title, category_id, location_id,
        COALESCE(p_sale_price, price_amount), price_currency, NOW()
    FROM products
    WHERE id = p_product_id;

    -- Update product status
    UPDATE products
    SET status = 'sold',
        updated_at = NOW()
    WHERE id = p_product_id;

    COMMIT;
END$$

-- Get product recommendations based on category, price, and condition similarity
DROP PROCEDURE IF EXISTS GetProductRecommendations$$
CREATE PROCEDURE GetProductRecommendations(
    IN p_product_id INT,
    IN p_limit INT
)
BEGIN
    -- Declare variables
    DECLARE v_category_id INT;
    DECLARE v_price DECIMAL(12,2);
    DECLARE v_condition VARCHAR(50);
    
    -- Get current product details for comparison
    SELECT category_id, price_amount, `condition`
    INTO v_category_id, v_price, v_condition
    FROM products
    WHERE id = p_product_id;
    
    -- Get recommendations based on similarity
    SELECT 
        p.id,
        p.title,
        p.price_amount,
        p.price_currency,
        p.condition,
        p.views_count,
        p.likes_count,
        (SELECT pi.url 
         FROM product_images pi 
         WHERE pi.product_id = p.id 
         ORDER BY pi.sort_order ASC 
         LIMIT 1) AS image_url,
        -- Similarity score calculation
        (
            CASE WHEN p.category_id = v_category_id THEN 3 ELSE 0 END +
            CASE WHEN v_price IS NOT NULL AND ABS(p.price_amount - v_price) < (v_price * 0.3) THEN 2 ELSE 0 END +
            CASE WHEN p.condition = v_condition THEN 1 ELSE 0 END +
            (p.likes_count * 0.1) + (p.views_count * 0.05)
        ) AS similarity_score
    FROM products p
    WHERE p.id != p_product_id
      AND p.status = 'active'
    ORDER BY similarity_score DESC, p.created_at DESC
    LIMIT p_limit;
END$$

-- Get recent user signups
DROP PROCEDURE IF EXISTS GetRecentSignups$$
CREATE PROCEDURE GetRecentSignups(IN p_limit INT)
BEGIN
    SELECT id AS user_id, username, full_name, email, created_at
    FROM users
    ORDER BY created_at DESC
    LIMIT p_limit;
END$$

-- Get recent product creations
DROP PROCEDURE IF EXISTS GetRecentProductCreations$$
CREATE PROCEDURE GetRecentProductCreations(IN p_limit INT)
BEGIN
    SELECT p.id AS product_id, p.title, p.seller_id, u.username AS seller_username, p.created_at
    FROM products p
    LEFT JOIN users u ON p.seller_id = u.id
    ORDER BY p.created_at DESC
    LIMIT p_limit;
END$$

-- Get recent favorites (who favorited which product and when)
DROP PROCEDURE IF EXISTS GetRecentFavorites$$
CREATE PROCEDURE GetRecentFavorites(IN p_limit INT)
BEGIN
    SELECT f.user_id, u.username, f.product_id, p.title, f.created_at AS favorited_at
    FROM favorites f
    LEFT JOIN users u ON f.user_id = u.id
    LEFT JOIN products p ON f.product_id = p.id
    ORDER BY f.created_at DESC
    LIMIT p_limit;
END$$

-- Get recent view history for a given user
DROP PROCEDURE IF EXISTS GetUserViewHistory$$
CREATE PROCEDURE GetUserViewHistory(IN p_user_id INT, IN p_limit INT)
BEGIN
    SELECT
        iv.product_id,
        p.title,
        p.price_amount,
        p.price_currency,
        iv.viewed_at,
        iv.session_id,
        iv.user_agent,
        (SELECT pi.url 
         FROM product_images pi 
         WHERE pi.product_id = p.id 
         ORDER BY pi.sort_order ASC 
         LIMIT 1) AS image_url
    FROM item_views iv
    JOIN products p ON iv.product_id = p.id
    WHERE iv.viewer_user_id = p_user_id
    ORDER BY iv.viewed_at DESC
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

-- A view that shows only active products with essential details for public listing.
DROP VIEW IF EXISTS vw_public_products;
CREATE VIEW vw_public_products AS
SELECT 
    p.id,
    p.title,
    p.price_amount,
    p.price_currency,
    p.status,
    (SELECT pi.url 
     FROM product_images pi 
     WHERE pi.product_id = p.id 
     ORDER BY pi.sort_order ASC 
     LIMIT 1) AS image_url
FROM products p
WHERE p.status = 'active';

-- Popular products by favorites and views
DROP VIEW IF EXISTS vw_popular_products;
CREATE VIEW vw_popular_products AS
SELECT 
    p.id,
    p.title,
    p.price_amount,
    p.price_currency,
    p.status,
    COUNT(DISTINCT CONCAT(f.user_id, '-', f.product_id)) AS favorite_count,
    COUNT(DISTINCT iv.id) AS view_count,
    (COUNT(DISTINCT CONCAT(f.user_id, '-', f.product_id)) * 2 + COUNT(DISTINCT iv.id)) AS popularity_score,
    (SELECT pi.url 
     FROM product_images pi 
     WHERE pi.product_id = p.id 
     ORDER BY pi.sort_order ASC 
     LIMIT 1) AS image_url
FROM products p
LEFT JOIN favorites f ON p.id = f.product_id
LEFT JOIN item_views iv ON p.id = iv.product_id
WHERE p.status = 'active'
GROUP BY p.id, p.title, p.price_amount, p.price_currency, p.status
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
-- COUNTER TRIGGERS (Auto-maintain views_count & likes_count)
-- ============================================

-- Trigger: Increment views_count when a view is added
DROP TRIGGER IF EXISTS trg_item_views_after_insert;
DELIMITER $$
CREATE TRIGGER trg_item_views_after_insert
AFTER INSERT ON item_views
FOR EACH ROW
BEGIN
    UPDATE products
    SET views_count = views_count + 1
    WHERE id = NEW.product_id;
END$$
DELIMITER ;

-- Trigger: Decrement views_count when a view is deleted
DROP TRIGGER IF EXISTS trg_item_views_after_delete;
DELIMITER $$
CREATE TRIGGER trg_item_views_after_delete
AFTER DELETE ON item_views
FOR EACH ROW
BEGIN
    UPDATE products
    SET views_count = GREATEST(views_count - 1, 0)
    WHERE id = OLD.product_id;
END$$
DELIMITER ;

-- Trigger: Increment likes_count when a favorite is added
DROP TRIGGER IF EXISTS trg_favorites_after_insert;
DELIMITER $$
CREATE TRIGGER trg_favorites_after_insert
AFTER INSERT ON favorites
FOR EACH ROW
BEGIN
    UPDATE products
    SET likes_count = likes_count + 1
    WHERE id = NEW.product_id;
END$$
DELIMITER ;

-- Trigger: Decrement likes_count when a favorite is removed
DROP TRIGGER IF EXISTS trg_favorites_after_delete;
DELIMITER $$
CREATE TRIGGER trg_favorites_after_delete
AFTER DELETE ON favorites
FOR EACH ROW
BEGIN
    UPDATE products
    SET likes_count = GREATEST(likes_count - 1, 0)
    WHERE id = OLD.product_id;
END$$
DELIMITER ;

-- ============================================
-- EVENTS (Scheduled Tasks)
-- ============================================

-- Enable event scheduler
SET GLOBAL event_scheduler = ON;

-- Event: Mark old inactive products as paused (runs daily at 2 AM)
DROP EVENT IF EXISTS evt_expire_old_products;
DELIMITER $$
CREATE EVENT evt_expire_old_products
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    UPDATE products
    SET status = 'paused',
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
-- ============================================
-- COMPLETION MESSAGE
-- ============================================
SELECT 'Database stored objects initialized successfully!' AS message;
