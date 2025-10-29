-- ============================================
-- DATABASE USERS & PRIVILEGES
-- Creates users with appropriate permissions
-- Run this manually with root credentials
-- ============================================

-- ============================================
-- 1. APPLICATION USER (Minimum privileges for CRUD)
-- ============================================
CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'app_secure_password';

-- Grant basic CRUD privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON marketplace.* TO 'app_user'@'%';

-- Grant execute for stored procedures and functions
GRANT EXECUTE ON marketplace.* TO 'app_user'@'%';

-- Explicitly revoke dangerous privileges
REVOKE DROP, CREATE, ALTER, INDEX, REFERENCES ON marketplace.* FROM 'app_user'@'%';

-- ============================================
-- 2. ADMIN USER (Full privileges)
-- ============================================
CREATE USER IF NOT EXISTS 'db_admin'@'%' IDENTIFIED BY 'admin_secure_password';

-- Grant all privileges with grant option
GRANT ALL PRIVILEGES ON marketplace.* TO 'db_admin'@'%' WITH GRANT OPTION;

-- ============================================
-- 3. READ-ONLY USER (For analytics, reports)
-- ============================================
CREATE USER IF NOT EXISTS 'readonly_user'@'%' IDENTIFIED BY 'readonly_password';

-- Grant select on all tables
GRANT SELECT ON marketplace.* TO 'readonly_user'@'%';

-- Can also execute functions for read operations
GRANT EXECUTE ON FUNCTION marketplace.GetUserRating TO 'readonly_user'@'%';
GRANT EXECUTE ON FUNCTION marketplace.GetProductAgeDays TO 'readonly_user'@'%';

-- ============================================
-- 4. RESTRICTED READ USER (Cannot see sensitive data)
-- ============================================
CREATE USER IF NOT EXISTS 'restricted_user'@'%' IDENTIFIED BY 'restricted_password';

-- Grant select only on non-sensitive tables
GRANT SELECT ON marketplace.products TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.categories TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.locations TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.product_images TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.colors TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.materials TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.tags TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.product_colors TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.product_materials TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.product_tags TO 'restricted_user'@'%';

-- Grant access to public views only
GRANT SELECT ON marketplace.vw_public_products TO 'restricted_user'@'%';
GRANT SELECT ON marketplace.vw_popular_products TO 'restricted_user'@'%';

-- Explicitly cannot access: users, messages, conversations, favorites, 
-- sold_item_archive, product_audit, item_views

-- ============================================
-- APPLY CHANGES
-- ============================================
FLUSH PRIVILEGES;

-- ============================================
-- VERIFY USERS
-- ============================================
SELECT 
    User, 
    Host,
    plugin as auth_plugin
FROM mysql.user 
WHERE User IN ('app_user', 'db_admin', 'readonly_user', 'restricted_user')
ORDER BY User;

-- ============================================
-- VIEW GRANTS (Uncomment to check)
-- ============================================
-- SHOW GRANTS FOR 'app_user'@'%';
-- SHOW GRANTS FOR 'db_admin'@'%';
-- SHOW GRANTS FOR 'readonly_user'@'%';
-- SHOW GRANTS FOR 'restricted_user'@'%';

SELECT 'Database users created successfully!' AS message;
