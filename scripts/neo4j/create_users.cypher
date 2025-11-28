// ============================================
// NEO4J DATABASE USERS & ROLES
// Creates users with appropriate permissions
// Run this in Neo4j Browser or with cypher-shell
// ============================================

// ============================================
// 1. APPLICATION USER (CRUD privileges)
// ============================================
// Create user with read and write access to marketplace database
CREATE USER app_user
SET PASSWORD 'app_secure_password'
CHANGE NOT REQUIRED;

GRANT ROLE reader TO app_user;
GRANT ROLE editor TO app_user;
GRANT ACCESS ON DATABASE marketplace TO app_user;
GRANT MATCH {*} ON GRAPH marketplace TO app_user;
GRANT CREATE ON GRAPH marketplace TO app_user;
GRANT DELETE ON GRAPH marketplace TO app_user;
GRANT SET PROPERTY ON GRAPH marketplace TO app_user;

// ============================================
// 2. ADMIN USER (Full privileges)
// ============================================
CREATE USER db_admin
SET PASSWORD 'admin_secure_password'
CHANGE NOT REQUIRED;

GRANT ROLE admin TO db_admin;
GRANT ACCESS ON DATABASE marketplace TO db_admin;
GRANT ALL GRAPH PRIVILEGES ON GRAPH marketplace TO db_admin;

// ============================================
// 3. READ-ONLY USER (For analytics, reports)
// ============================================
CREATE USER readonly_user
SET PASSWORD 'readonly_password'
CHANGE NOT REQUIRED;

GRANT ROLE reader TO readonly_user;
GRANT ACCESS ON DATABASE marketplace TO readonly_user;
GRANT MATCH {*} ON GRAPH marketplace TO readonly_user;

// ============================================
// 4. RESTRICTED READ USER (Limited node types)
// ============================================
CREATE USER restricted_user
SET PASSWORD 'restricted_password'
CHANGE NOT REQUIRED;

GRANT ROLE reader TO restricted_user;
GRANT ACCESS ON DATABASE marketplace TO restricted_user;

// Grant read access only to specific node labels
GRANT MATCH {label: Product} ON GRAPH marketplace TO restricted_user;
GRANT MATCH {label: Category} ON GRAPH marketplace TO restricted_user;
GRANT MATCH {label: Location} ON GRAPH marketplace TO restricted_user;

// Explicitly deny access to sensitive node types
DENY MATCH {label: User} ON GRAPH marketplace TO restricted_user;
DENY MATCH {label: Message} ON GRAPH marketplace TO restricted_user;
DENY MATCH {label: Conversation} ON GRAPH marketplace TO restricted_user;

// ============================================
// VERIFY USERS
// ============================================
SHOW USERS;

// ============================================
// SHOW ROLES AND PRIVILEGES (uncomment to check)
// ============================================
// SHOW USER app_user PRIVILEGES;
// SHOW USER db_admin PRIVILEGES;
// SHOW USER readonly_user PRIVILEGES;
// SHOW USER restricted_user PRIVILEGES;

// ============================================
// USAGE INSTRUCTIONS
// ============================================
// Local connection with specific user:
//   neo4j://localhost:7687
//   Username: app_user / readonly_user / restricted_user
//   Password: [respective password]
//
// Cloud Neo4j AuraDB connection:
//   neo4j+s://[your-instance].databases.neo4j.io
//   Create users in AuraDB console or via cypher-shell
//
// Cypher-shell example:
//   cypher-shell -u app_user -p app_secure_password -a bolt://localhost:7687
//
// Python driver example:
//   driver = GraphDatabase.driver("bolt://localhost:7687", 
//                                 auth=("app_user", "app_secure_password"))

// ============================================
// NOTES FOR NEO4J AURADB (CLOUD)
// ============================================
// AuraDB Professional/Enterprise support multiple users
// AuraDB Free tier has limited user management
// For AuraDB, create users through the console or connect as admin and run these commands
// Adjust database name if different from 'marketplace'
