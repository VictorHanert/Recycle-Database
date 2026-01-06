# API Testing Guide - MongoDB & Neo4j

Complete guide for testing both document (MongoDB) and graph (Neo4j) database endpoints.

## Quick Setup

### 1. Import into Postman

**Import Collection:**
- Open Postman
- Click **Import** → **File**
- Select `marketplace-collection.json`

**Import Environment:**
- Click **Import** → **File**  
- Select `marketplace-environment.json`
- Select environment from dropdown (top right)

### 2. Start Services

```bash
docker compose up -d
```

Wait for services to be ready (~30 seconds).

---

## Testing Workflow

### MongoDB Testing Flow

#### Step 1: Register a MongoDB User
```
POST /mongodb/auth/register
```
**Body:**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "testpassword123",
  "full_name": "Test User",
  "phone": "+45 12345678"
}
```

✅ **Auto-saves:** `mongodb_token` and `mongodb_user_id` to environment

#### Step 2: Create a Product
```
POST /mongodb/products
Authorization: Bearer {{mongodb_token}}
```
**Body:**
```json
{
  "title": "Vintage Bicycle",
  "description": "Well-maintained vintage bike",
  "price_amount": 500.00,
  "price_currency": "DKK",
  "product_condition": "used",
  "colors": ["blue", "white"],
  "materials": ["metal", "rubber"],
  "tags": ["bicycle", "vintage"]
}
```

✅ **Auto-saves:** `mongodb_product_id` to environment

#### Step 3: Test Product Endpoints

**Get All Products** (no auth required)
```
GET /mongodb/products?skip=0&limit=20
```

**Search Products**
```
GET /mongodb/products/search?q=bicycle
```

**Filter Products**
```
GET /mongodb/products/filter?status=active
```

**Get Popular Products**
```
GET /mongodb/products/popular?limit=10
```

**Update Product** (requires auth)
```
PUT /mongodb/products/{{mongodb_product_id}}
Authorization: Bearer {{mongodb_token}}
```
**Body:**
```json
{
  "title": "Vintage Bicycle - Updated",
  "price_amount": 450.00
}
```

**Mark as Sold**
```
PATCH /mongodb/products/{{mongodb_product_id}}/mark-sold
Authorization: Bearer {{mongodb_token}}
```

**Record View**
```
POST /mongodb/products/{{mongodb_product_id}}/view
Authorization: Bearer {{mongodb_token}}
```

---

### Neo4j Testing Flow

#### Step 1: Register a Neo4j User
```
POST /neo4j/auth/register
```
**Body:**
```json
{
  "username": "neo4j_testuser",
  "email": "neo4j_test@example.com",
  "password": "testpassword123",
  "full_name": "Neo4j Test User"
}
```

✅ **Auto-saves:** `neo4j_token` to environment

#### Step 2: Create a Product
```
POST /neo4j/products
Authorization: Bearer {{neo4j_token}}
```
**Body:**
```json
{
  "title": "Neo4j Vintage Bicycle",
  "description": "Graph database test product",
  "price_amount": 600.00,
  "price_currency": "DKK",
  "product_condition": "used"
}
```

✅ **Auto-saves:** `neo4j_product_id` to environment

#### Step 3: Test Graph Endpoints

**Get All Products**
```
GET /neo4j/products?skip=0&limit=20
```

**Get Products by Seller** (Graph-specific!)
```
GET /neo4j/products/seller/neo4j_testuser
```

**Update Product**
```
PUT /neo4j/products/{{neo4j_product_id}}
Authorization: Bearer {{neo4j_token}}
```

---

## Environment Variables Reference

| Variable | Description | Auto-populated |
|----------|-------------|----------------|
| `base_url` | API base URL | ❌ (set to localhost:8001) |
| `username` | Test username | ❌ |
| `password` | Test password | ❌ |
| `email` | Test email | ❌ |
| `full_name` | Test full name | ❌ |
| `mongodb_token` | MongoDB JWT token | ✅ (on login/register) |
| `mongodb_user_id` | MongoDB user ID | ✅ (on register) |
| `mongodb_product_id` | MongoDB product ID | ✅ (on product create) |
| `neo4j_token` | Neo4j JWT token | ✅ (on login/register) |
| `neo4j_product_id` | Neo4j product ID | ✅ (on product create) |

---

## Complete Endpoint List

### MongoDB Endpoints

#### Auth
- `POST /mongodb/auth/register` - Register new user
- `POST /mongodb/auth/login` - Login user

#### Users
- `GET /mongodb/users` - List all users (paginated)
- `GET /mongodb/users/{user_id}` - Get user by ID
- `GET /mongodb/users/username/{username}` - Get user by username
- `DELETE /mongodb/users/{user_id}` - Delete user (admin)

#### Products
- `POST /mongodb/products` - Create product 🔒
- `GET /mongodb/products` - List products (paginated)
- `GET /mongodb/products/{product_id}` - Get product by ID
- `GET /mongodb/products/search` - Full-text search
- `GET /mongodb/products/filter` - Filter by status/seller/category
- `GET /mongodb/products/popular` - Get popular products
- `GET /mongodb/products/top-categories` - Get category stats
- `PUT /mongodb/products/{product_id}` - Update product 🔒
- `PATCH /mongodb/products/{product_id}/mark-sold` - Mark as sold 🔒
- `PATCH /mongodb/products/{product_id}/toggle-status` - Toggle status 🔒
- `POST /mongodb/products/{product_id}/view` - Record view 🔒
- `DELETE /mongodb/products/{product_id}` - Delete product 🔒

### Neo4j Endpoints

#### Auth
- `POST /neo4j/auth/register` - Register new user
- `POST /neo4j/auth/login` - Login user

#### Users
- `GET /neo4j/users` - List all users
- `GET /neo4j/users/{username}` - Get user by username

#### Products
- `POST /neo4j/products` - Create product 🔒
- `GET /neo4j/products` - List products (paginated)
- `GET /neo4j/products/{product_id}` - Get product by ID
- `GET /neo4j/products/seller/{username}` - Get products by seller
- `PUT /neo4j/products/{product_id}` - Update product 🔒
- `DELETE /neo4j/products/{product_id}` - Delete product 🔒

🔒 = Requires authentication

---

## Sample Test Scenarios

### Scenario 1: Complete MongoDB Flow
1. Register user → Save token
2. Create product → Save product ID
3. Get all products → Verify product exists
4. Search for product → Test text search
5. Update product → Change price
6. Record view → Increment view count
7. Mark as sold → Change status

### Scenario 2: Complete Neo4j Flow
1. Register user → Save token
2. Create product → Creates SELLS relationship
3. Get products by seller → Test graph traversal
4. Update product → Modify node properties
5. Delete product → Remove node and relationships

### Scenario 3: Compare Databases
1. Create same product in both DBs
2. Search/filter in MongoDB (document queries)
3. Graph traversal in Neo4j (relationship queries)
4. Compare response times and data structure

---

## API Documentation

**Interactive Docs:**
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

**Health Check:**
```bash
curl http://localhost:8001/health
```

---

## Troubleshooting

**Token expired:**
- Re-run the login request for the respective database
- Token is auto-saved to environment variables

**Product not found:**
- Ensure you created a product first
- Check that `mongodb_product_id` or `neo4j_product_id` is set

**Unauthorized (401):**
- Check that the token variable is set
- Verify Authorization header: `Bearer {{mongodb_token}}`
- Make sure you're using the correct token for each database

**User not found in MongoDB:**
- MongoDB products require the user to exist in MongoDB
- Register through `/mongodb/auth/register` first

---

## Advanced Testing

### Using Existing Migrated Data

If you've run migrations, you can test with existing users:

**MongoDB:**
```bash
mongosh "mongodb://app_user:app_secure_password@localhost:27017/marketplace"
db.users.find().limit(5)
```

Copy a username and login with their credentials (if you know the password from migration source).

### Comparing Query Performance

Use Postman's test scripts to measure response times:

```javascript
// Add to Tests tab
const responseTime = pm.response.responseTime;
console.log(`Response time: ${responseTime}ms`);
pm.environment.set('last_response_time', responseTime);
```

Compare MongoDB vs Neo4j for:
- Simple product list
- Search/filter operations
- Graph traversals (Neo4j specialty)

---

## Next Steps

1. ✅ Import collection and environment
2. ✅ Start services
3. ✅ Test MongoDB endpoints
4. ✅ Test Neo4j endpoints
5. ✅ Compare database approaches
6. 📊 Analyze which patterns work best for each DB type
