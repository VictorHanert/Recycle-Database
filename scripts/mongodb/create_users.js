// ============================================
// MONGODB DATABASE USERS & ROLES
// Creates users with appropriate permissions
// Run this in MongoDB shell or with mongosh
// ============================================

// Switch to admin database to create users
use admin;

// ============================================
// 1. APPLICATION USER (CRUD privileges only)
// ============================================
db.createUser({
  user: "app_user",
  pwd: "app_secure_password",
  roles: [
    {
      role: "readWrite",
      db: "marketplace"
    }
  ]
});

print("✓ Created app_user with readWrite access to marketplace database");

// ============================================
// 2. ADMIN USER (Full privileges)
// ============================================
db.createUser({
  user: "db_admin",
  pwd: "admin_secure_password",
  roles: [
    {
      role: "dbOwner",
      db: "marketplace"
    },
    {
      role: "userAdmin",
      db: "marketplace"
    }
  ]
});

print("✓ Created db_admin with full database owner privileges");

// ============================================
// 3. READ-ONLY USER (For analytics, reports)
// ============================================
db.createUser({
  user: "readonly_user",
  pwd: "readonly_password",
  roles: [
    {
      role: "read",
      db: "marketplace"
    }
  ]
});

print("✓ Created readonly_user with read-only access");

// ============================================
// 4. RESTRICTED READ USER (Limited collections)
// ============================================
// First, create a custom role for restricted access
use marketplace;

db.createRole({
  role: "restrictedReader",
  privileges: [
    {
      resource: { db: "marketplace", collection: "products" },
      actions: ["find"]
    },
    {
      resource: { db: "marketplace", collection: "categories" },
      actions: ["find"]
    },
    {
      resource: { db: "marketplace", collection: "locations" },
      actions: ["find"]
    },
    {
      resource: { db: "marketplace", collection: "product_views" },
      actions: ["find"]
    }
  ],
  roles: []
});

print("✓ Created restrictedReader custom role");

// Create the restricted user
use admin;

db.createUser({
  user: "restricted_user",
  pwd: "restricted_password",
  roles: [
    {
      role: "restrictedReader",
      db: "marketplace"
    }
  ]
});

print("✓ Created restricted_user with limited collection access");

// ============================================
// VERIFY USERS
// ============================================
use admin;

print("\n=== Database Users Created ===");
db.system.users.find({}, { user: 1, roles: 1, _id: 0 }).forEach(printjson);

// ============================================
// USAGE INSTRUCTIONS
// ============================================
print("\n=== Usage Instructions ===");
print("Connect as app_user:");
print("  mongosh 'mongodb://app_user:app_secure_password@localhost:27017/marketplace'");
print("");
print("Connect as readonly_user:");
print("  mongosh 'mongodb://readonly_user:readonly_password@localhost:27017/marketplace'");
print("");
print("Connect as restricted_user:");
print("  mongosh 'mongodb://restricted_user:restricted_password@localhost:27017/marketplace'");
print("");
print("Cloud MongoDB Atlas connection:");
print("  Replace credentials in connection string with specific user");
print("  mongodb+srv://app_user:app_secure_password@cluster.mongodb.net/marketplace");
