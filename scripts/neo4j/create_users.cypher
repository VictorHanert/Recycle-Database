// ============================================
// NEO4J DATABASE USERS
// Community Edition (no role-based access control)
// Create users with basic authentication (idempotent)
// ============================================

// ============================================
// 1. APPLICATION USER (For application access)
// ============================================
CREATE USER app_user IF NOT EXISTS
SET PASSWORD 'app_secure_password'
CHANGE NOT REQUIRED;

// ============================================
// 2. ADMIN USER (Full access)
// ============================================
CREATE USER db_admin IF NOT EXISTS
SET PASSWORD 'admin_secure_password'
CHANGE NOT REQUIRED;

// ============================================
// 3. READ-ONLY USER (For analytics, reports)
// ============================================
CREATE USER readonly_user IF NOT EXISTS
SET PASSWORD 'readonly_password'
CHANGE NOT REQUIRED;

// ============================================
// 4. RESTRICTED READ USER (Limited access)
// ============================================
CREATE USER restricted_user IF NOT EXISTS
SET PASSWORD 'restricted_password'
CHANGE NOT REQUIRED;

// ============================================
// VERIFY USERS
// ============================================
SHOW USERS;

// ============================================
// NOTES FOR NEO4J
// ============================================
// Community Edition: Basic user/password authentication only
// Enterprise Edition (cloud/paid): Full role-based access control with GRANT/DENY
// 
// All users created above can connect to Neo4j with their credentials.
// Data access control is not enforced in Community Edition.
// Implement application-level authorization in your code if needed.
//
// Connection examples:
//   cypher-shell -u app_user -p app_secure_password -a bolt://localhost:7687
//   driver = GraphDatabase.driver("bolt://localhost:7687", 
//                                 auth=("app_user", "app_secure_password"))
