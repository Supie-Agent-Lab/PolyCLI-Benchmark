## 1. Introduction and Purpose

This document serves as the central knowledge repository for the project's backend, capturing critical technical solutions, common error resolutions, and significant architectural patterns discovered during development. Its primary purpose is to provide developers with a single source of truth containing actionable guidance.

Refer to this guide to quickly troubleshoot recurring problems, implement established workarounds, and understand the "why" behind our key design and implementation choices. Treat this as a living playbook; it should be the first place you look for a solution and the last place you visit to document a new one you've discovered.

## 2. Database: Legacy Connectivity & Data Migration

### 2.1 Connecting to the Legacy Oracle 8i Database

Connecting to the legacy Oracle 8i database requires a specific, older JDBC driver due to outdated authentication protocols not supported by modern drivers.

**Required JDBC Driver**

-   **Driver File:** `ojdbc14.jar`
-   **Reason:** This driver is one of the last versions to support the authentication protocol used by Oracle 8i (and 9i/10g). Newer drivers like `ojdbc8.jar` will fail to connect because they enforce stricter, more modern security standards.
-   **Location:** The `ojdbc14.jar` file is committed to the legacy application's source repository under `/lib/`. Ensure it is included in the classpath of any application that needs to connect to this database.

**JDBC Connection String**

The connection must use the Oracle Thin Driver format.

-   **Format:** `jdbc:oracle:thin:@<host>:<port>:<SID>`
-   **Concrete Example:**
    ```
    jdbc:oracle:thin:@legacy-db.internal.corp:1521:ORCL8I
    ```

**Java Code Example for Connection**

This snippet demonstrates how to establish a connection in a Java application. Note the use of `Class.forName()`, a common pattern in older JDBC implementations.

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class Oracle8iConnector {

    private static final String DB_DRIVER = "oracle.jdbc.driver.OracleDriver";
    private static final String DB_CONNECTION_URL = "jdbc:oracle:thin:@legacy-db.internal.corp:1521:ORCL8I";
    private static final String DB_USER = "legacy_user";
    private static final String DB_PASSWORD = "your_secret_password";

    public Connection getConnection() throws SQLException {
        Connection dbConnection = null;
        try {
            Class.forName(DB_DRIVER);
        } catch (ClassNotFoundException e) {
            System.err.println("Oracle JDBC Driver not found: " + e.getMessage());
            // This error means ojdbc14.jar is not in the classpath.
            throw new SQLException("JDBC Driver registration failed.", e);
        }

        try {
            dbConnection = DriverManager.getConnection(DB_CONNECTION_URL, DB_USER, DB_PASSWORD);
            return dbConnection;
        } catch (SQLException e) {
            System.err.println("Connection Failed! Check output console");
            // Log the full exception for debugging.
            e.printStackTrace();
            throw e;
        }
    }
}
```

**Common Errors and Solutions**

-   **Error:**
    ```
    java.sql.SQLException: ORA-28040: No matching authentication protocol
    ```
    -   **Cause:** Using a modern JDBC driver (e.g., `ojdbc8.jar` from Oracle 12c/18c/19c) or a modern JDK (JDK 8+) with default security settings against the Oracle 8i database.
    -   **Solution:** **You must use `ojdbc14.jar`.** There is no workaround with modern drivers. Ensure your project's build path or lib directory exclusively contains `ojdbc14.jar` for this specific connection.

-   **Error:**
    ```
    java.lang.ClassNotFoundException: oracle.jdbc.driver.OracleDriver
    ```
    -   **Cause:** The `ojdbc14.jar` file is not present in the application's runtime classpath.
    -   **Solution:** For a web application, place `ojdbc14.jar` in the `WEB-INF/lib` folder. For a standalone Java application, ensure it's included via the `-cp` or `--class-path` command-line argument.

---

### 2.2 Python Script for Data Migration to PostgreSQL

This section details a reusable Python script for extracting data from the Oracle 8i database and loading it into a new PostgreSQL instance. The script leverages `pandas` for data handling and `psycopg2` for PostgreSQL communication. For Oracle connectivity, it uses the `cx_Oracle` library, which requires the Oracle Instant Client.

**Prerequisites**

1.  **Install Python Packages:**
    ```bash
    pip install pandas psycopg2-binary cx_Oracle
    ```

2.  **Oracle Instant Client:** The `cx_Oracle` library is a wrapper around the Oracle OCI libraries. You must download and configure the Oracle Instant Client.
    -   **Action:** Download the Instant Client Basic or Basic Light package for your architecture. Version 19.8 is known to work well for connecting to older databases.
    -   **Configuration (Recommended):** Place the unzipped client in a known location and point to it at the beginning of your script. This avoids environment variable issues. Example:
        ```python
        import cx_Oracle
        # For Linux/macOS
        cx_Oracle.init_oracle_client(lib_dir="/opt/oracle/instantclient_19_8")
        # For Windows
        # cx_Oracle.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_8")
        ```

**Full Data Migration Script**

This script extracts user data from an `APP_USERS` table in Oracle, renames columns to follow a new convention, and inserts the records into a `users` table in PostgreSQL.

```python
import cx_Oracle
import psycopg2
import pandas as pd
import os

# --- Configuration ---

# Recommended: Use environment variables for credentials
ORACLE_USER = os.environ.get("ORA_USER", "legacy_user")
ORACLE_PW = os.environ.get("ORA_PW", "your_oracle_password")
# Oracle DSN (Data Source Name)
ORACLE_DSN = "legacy-db.internal.corp:1521/ORCL8I"

POSTGRES_DB = os.environ.get("PG_DB", "new_app_db")
POSTGRES_USER = os.environ.get("PG_USER", "new_user")
POSTGRES_PW = os.environ.get("PG_PW", "your_postgres_password")
POSTGRES_HOST = os.environ.get("PG_HOST", "postgres.internal.corp")

# Initialize Oracle Client (Update path as needed)
try:
    cx_Oracle.init_oracle_client(lib_dir="/opt/oracle/instantclient_19_8")
except cx_Oracle.Error as e:
    print("Error initializing Oracle Client:", e)
    print("Please ensure the Oracle Instant Client is correctly installed and the path is set.")
    exit(1)


def migrate_users():
    """
    Extracts user data from Oracle, transforms it, and loads it into PostgreSQL.
    """
    
    # --- 1. Extract Data from Oracle ---
    try:
        print("Connecting to Oracle...")
        oracle_conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PW, dsn=ORACLE_DSN)
        print("Oracle connection successful.")

        # Note: Oracle table/column names are often uppercase
        sql_query = "SELECT USER_ID, USERNAME, EMAIL, CREATED_DATE FROM APP_USERS"
        df = pd.read_sql_query(sql_query, oracle_conn)
        print(f"Extracted {len(df)} rows from Oracle.")

    except cx_Oracle.Error as e:
        print(f"Error connecting to or reading from Oracle: {e}")
        return
    finally:
        if 'oracle_conn' in locals() and oracle_conn:
            oracle_conn.close()
            print("Oracle connection closed.")

    if df.empty:
        print("No data to migrate. Exiting.")
        return

    # --- 2. Transform Data using Pandas ---
    print("Transforming data...")
    # Rename columns to match PostgreSQL schema conventions (snake_case)
    df.rename(columns={
        'USER_ID': 'legacy_id',
        'USERNAME': 'username',
        'EMAIL': 'email',
        'CREATED_DATE': 'created_at' # Oracle DATE type is read as datetime
    }, inplace=True)

    # Convert to standard Pandas datetime objects
    df['created_at'] = pd.to_datetime(df['created_at'])

    # Ensure no None values for non-nullable columns, replace with defaults if needed
    df['username'].fillna('unknown', inplace=True)


    # --- 3. Load Data into PostgreSQL ---
    pg_conn = None
    try:
        print("Connecting to PostgreSQL...")
        pg_conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PW,
            host=POSTGRES_HOST
        )
        print("PostgreSQL connection successful.")
        cursor = pg_conn.cursor()

        # Prepare the INSERT statement
        insert_query = """
            INSERT INTO users (legacy_id, username, email, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (legacy_id) DO NOTHING; -- Avoids errors on re-runs
        """

        # Create a list of tuples from the dataframe values
        data_tuples = [tuple(row) for row in df.itertuples(index=False)]

        # Execute the insert command
        cursor.executemany(insert_query, data_tuples)
        
        # Commit the transaction
        pg_conn.commit()
        print(f"Successfully inserted/updated {cursor.rowcount} records into PostgreSQL.")

    except (Exception, psycopg2.Error) as e:
        print(f"Error during PostgreSQL operation: {e}")
        if pg_conn:
            pg_conn.rollback() # Rollback on error
    finally:
        if pg_conn:
            cursor.close()
            pg_conn.close()
            print("PostgreSQL connection closed.")

if __name__ == "__main__":
    migrate_users()

```

**Potential Errors and Fixes**

-   **Error:**
    ```
    cx_Oracle.DatabaseError: DPI-1047: Cannot locate a 64-bit Oracle Client library.
    ```
    -   **Cause:** The Python script cannot find the Oracle Instant Client libraries.
    -   **Solution:** Ensure the path passed to `cx_Oracle.init_oracle_client(lib_dir=...)` is correct and points to the directory containing files like `liboci.so` (Linux) or `oci.dll` (Windows).

-   **Error:**
    ```
    psycopg2.errors.UndefinedTable: relation "users" does not exist
    ```
    -   **Cause:** The target table `users` has not been created in the PostgreSQL database.
    -   **Solution:** Before running the script, connect to PostgreSQL and create the table with the correct schema.
        ```sql
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            legacy_id INTEGER UNIQUE NOT NULL,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL
        );
        ```

-   **Error:**
    ```
    psycopg2.errors.InvalidTextRepresentation: invalid input syntax for type integer: "N/A"
    ```
    -   **Cause:** A data type mismatch. The script is trying to insert a string value (e.g., "N/A") from the Oracle source into a PostgreSQL column defined as `INTEGER`.
    -   **Solution:** Add a data cleaning step in the pandas transformation block to handle such cases before attempting the database insert.
        ```python
        # In the transformation section of the script...
        # Convert column to numeric, coercing errors into 'NaN' (Not a Number)
        df['legacy_id'] = pd.to_numeric(df['legacy_id'], errors='coerce')
        # Drop rows where the ID could not be converted, as they are invalid
        df.dropna(subset=['legacy_id'], inplace=True)
        # Convert the column to integer type now that it's clean
        df['legacy_id'] = df['legacy_id'].astype(int)
        ```

## 3. API Security and CORS Configuration

The API is secured using a stateless authentication mechanism, which prevents unauthorized access to protected endpoints. All client-server communication should happen over HTTPS. Server-side, Cross-Origin Resource Sharing (CORS) must be correctly configured to allow our frontend application to communicate with the API from a different domain.

### JWT Authentication Middleware

The API uses JSON Web Tokens (JWT) for authenticating requests. Protected routes require a valid JWT to be passed in the `Authorization` header using the `Bearer` scheme.

**Workflow:**
1.  A client authenticates via a login endpoint (e.g., `/api/auth/login`).
2.  Upon successful authentication, the server generates a signed JWT containing a payload (e.g., `userId`, `role`) and an expiration time.
3.  The client stores this token securely.
4.  For every subsequent request to a protected endpoint, the client must include the token in the `Authorization` header: `Authorization: Bearer <your_jwt>`.
5.  A Node.js/Express middleware intercepts each request, validates the token, and, if valid, attaches the decoded user information to the `request` object before passing it to the route handler.

If the token is missing, malformed, or invalid (e.g., expired or incorrect signature), the middleware immediately responds with a `401 Unauthorized` or `403 Forbidden` error, blocking access to the resource.

**Node.js/Express Middleware Code (`middleware/authenticateToken.js`):**

This middleware function verifies the JWT. It relies on the `jsonwebtoken` library and expects the JWT secret to be stored in an environment variable `JWT_SECRET`.

```javascript
const jwt = require('jsonwebtoken');

/**
 * Express middleware to authenticate requests using a JWT.
 * It expects the token to be in the 'Authorization' header with the 'Bearer' scheme.
 *
 * @param {object} req - Express request object.
 * @param {object} res - Express response object.
 * @param {function} next - Express next middleware function.
 */
function authenticateToken(req, res, next) {
  // Get the 'Authorization' header from the request
  const authHeader = req.headers['authorization'];
  
  // The header value is expected to be "Bearer TOKEN"
  // Split the string and get the token part.
  const token = authHeader && authHeader.split(' ')[1];

  // If no token is provided, send a 401 Unauthorized response
  if (token == null) {
    return res.status(401).json({ message: 'Unauthorized: No token provided.' });
  }

  // Verify the token using the secret key
  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    // If the token is invalid (e.g., expired, wrong signature), send a 403 Forbidden response
    if (err) {
      console.error('JWT Verification Error:', err.message);
      return res.status(403).json({ message: 'Forbidden: Token is not valid.' });
    }

    // If verification is successful, the 'user' object contains the decoded payload
    // Attach the user payload to the request object for use in subsequent route handlers
    req.user = user;

    // Proceed to the next middleware or route handler
    next();
  });
}

module.exports = authenticateToken;
```

---

### Solving CORS Policy Errors with Nginx

When the frontend application (e.g., running on `https://app.ourdomain.com`) tries to make a request to the API (e.g., at `https://api.ourdomain.com`), the browser's security model will block the request unless the API server explicitly permits it.

**Common Browser Error Message:**

```
Access to XMLHttpRequest at 'https://api.ourdomain.com/v1/users/me' from origin 'https://app.ourdomain.com' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

This error occurs because the server is not sending the required `Access-Control-Allow-*` headers in its response. For complex requests (which includes any request with an `Authorization` header), the browser first sends a pre-flight `OPTIONS` request to check if the actual request is safe to send. Our server must handle this `OPTIONS` request correctly.

**Solution: Nginx Reverse Proxy Configuration**

The definitive solution is to configure our Nginx reverse proxy, which sits in front of the Node.js API, to add the necessary CORS headers to all responses. This offloads the responsibility from the application code and ensures consistent behavior.

Below is the complete Nginx `location` block for the API. It correctly handles both regular requests and pre-flight `OPTIONS` requests.

**Nginx `location` Block Example (`/etc/nginx/sites-available/api.ourdomain.com`):**

```nginx
# Location block for our API backend
location /v1/ {
    # Set the specific origin of our frontend application.
    # Using a wildcard '*' is less secure and should be avoided in production.
    add_header 'Access-Control-Allow-Origin' 'https://app.ourdomain.com' always;

    # Specify the methods the client is allowed to use.
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;

    # Specify the headers the client is allowed to send in their request.
    # This is CRITICAL for JWT. It MUST include 'Authorization'.
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, DNT, X-Requested-With, Cache-Control' always;

    # Allow the browser to send credentials (cookies, authorization headers).
    add_header 'Access-Control-Allow-Credentials' 'true' always;

    # Browser pre-flight request handling for OPTIONS method.
    # This is a critical optimization. We intercept the OPTIONS request
    # and return a 204 No Content response immediately, without bothering the backend.
    if ($request_method = 'OPTIONS') {
        # Respond with 204 No Content and empty body.
        return 204;
    }

    # If it's not a pre-flight request, proxy it to our Node.js application.
    proxy_pass http://localhost:3000; # Assuming Node.js runs on port 3000
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Key directives explained:**
*   `add_header ... always;`: The `always` parameter ensures the header is added regardless of the response code (e.g., even for errors like `404` or `500`).
*   `Access-Control-Allow-Origin`: Must be the exact origin of your frontend. Do not use a trailing slash.
*   `Access-Control-Allow-Headers`: Must include `Authorization` for JWT to work and `Content-Type` for requests with a JSON body.
*   `if ($request_method = 'OPTIONS')`: This block efficiently handles the pre-flight check by returning an empty `204` response directly from Nginx, which satisfies the browser's security check without adding load to the Node.js application.

## 4. Troubleshooting: Common Errors and Fixes

### Problem: Application crashes with `java.lang.OutOfMemoryError`

This general error indicates the Java Virtual Machine (JVM) cannot allocate an object because it is out of memory, and no more memory could be made available by the garbage collector. The specific error message provides clues to the root cause.

---

#### 1. OutOfMemoryError: Java heap space

This is the most common `OutOfMemoryError`. It occurs when the application tries to create a new object in the heap, but there isn't enough free space to accommodate it. This can be caused by a memory leak or by an application that genuinely requires a larger heap to operate correctly.

**Error Message:**
```
Exception in thread "main" java.lang.OutOfMemoryError: Java heap space
```

**Solution:**
The primary fix is to increase the maximum heap size allocated to the JVM. You can also set the initial heap size to the same value as the maximum to avoid heap resizing pauses at startup.

**Exact JVM Command-Line Flags:**
Use the `-Xms` flag to set the initial heap size and `-Xmx` to set the maximum heap size.

*   **Example:** To start an application with an initial and maximum heap size of 4 gigabytes:
    ```bash
    java -Xms4g -Xmx4g -jar your-application.jar
    ```

---

#### 2. OutOfMemoryError: Metaspace

This error occurs when the Metaspace, the memory area holding class metadata, is exhausted. This is common in applications that dynamically generate and load a large number of classes, such as those using certain proxying or bytecode manipulation libraries, or during frequent hot deploys in an application server.

**Error Message:**
```
Exception in thread "main" java.lang.OutOfMemoryError: Metaspace
```

**Solution:**
Increase the maximum Metaspace size. Unlike the heap, Metaspace grows automatically by default. However, its maximum size can be capped. If you hit this error, you need to raise that cap.

**Exact JVM Command-Line Flags:**
Use the `-XX:MaxMetaspaceSize` flag to increase the limit.

*   **Example:** To set the maximum Metaspace size to 512 megabytes:
    ```bash
    java -XX:MaxMetaspaceSize=512m -jar your-application.jar
    ```

---

#### 3. OutOfMemoryError: GC overhead limit exceeded

This error is a protective mechanism. It's triggered when the JVM spends an excessive amount of time (by default, 98% of total time) doing Garbage Collection (GC) while reclaiming a very small amount of heap memory (less than 2% of the heap). Effectively, the application is grinding to a halt, making no progress because it's constantly garbage collecting. The root cause is almost always that the live data set barely fits into the available heap.

**Error Message:**
```
Exception in thread "main" java.lang.OutOfMemoryError: GC overhead limit exceeded
```

**Solution:**
The most common fix is the same as for the `Java heap space` error: increase the heap size. This gives the application more breathing room.

**Exact JVM Command-Line Flags:**
Use the `-Xmx` flag to increase the maximum heap size.

*   **Example:** To increase the maximum heap size to 8 gigabytes:
    ```bash
    java -Xmx8g -jar your-application.jar
    ```
*   **Workaround (Use with Caution):** In rare cases, you might want to disable this specific check, although this is not recommended as it can hide a serious memory leak and cause the application to become unresponsive.
    ```bash
    java -XX:-UseGCOverheadLimit -Xmx4g -jar your-application.jar
    ```

---
---

### Problem: Database transactions fail with deadlock errors

A deadlock occurs when two or more transactions are waiting for each other to release locks, creating a circular dependency that can never be resolved without intervention. The database detects this cycle and terminates one of the transactions, rolling it back and returning a deadlock error to the application.

**Error Message (PostgreSQL Example):**
```
ERROR: deadlock detected
DETAIL: Process 12345 waits for ShareLock on transaction 67890; blocked by process 54321.
Process 54321 waits for ShareLock on transaction 0; blocked by process 12345.
```

**Scenario:**
Consider a `transfers` service that moves funds between two accounts in the `accounts` table. Two concurrent requests arrive:
1.  Transfer $100 from account `ID=1` to account `ID=2`.
2.  Transfer $50 from account `ID=2` to account `ID=1`.

The application logic for both transactions updates the two accounts in a different order.

**Root Cause:**
The deadlock happens due to inconsistent lock acquisition order.

1.  **Transaction 1** starts and places an exclusive `UPDATE` lock on the row for `account_id = 1`.
2.  **Transaction 2** starts and places an exclusive `UPDATE` lock on the row for `account_id = 2`.
3.  **Transaction 1** now attempts to `UPDATE` the row for `account_id = 2`, but it's locked by Transaction 2. Transaction 1 waits.
4.  **Transaction 2** now attempts to `UPDATE` the row for `account_id = 1`, but it's locked by Transaction 1. Transaction 2 waits.
5.  **DEADLOCK:** T1 is waiting for T2, and T2 is waiting for T1.

---

**Solution:**
The fix is to enforce a consistent locking order for all transactions. A robust pattern is to use `SELECT ... FOR UPDATE` to acquire all necessary row-level locks upfront, in a deterministic order (e.g., by ascending primary key), *before* performing any modifications. This ensures that a competing transaction cannot begin its work until the first one has acquired all its required locks.

#### Before (Deadlock-Prone Code):

The logic performs updates as it goes, leading to an unpredictable lock order.

**Transaction 1:**
```sql
BEGIN TRANSACTION;
-- Lock on account 1 acquired first
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- Now attempts to lock account 2, might have to wait
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
```

**Transaction 2 (Concurrent):**
```sql
BEGIN TRANSACTION;
-- Lock on account 2 acquired first
UPDATE accounts SET balance = balance - 50 WHERE id = 2;
-- Now attempts to lock account 1, might have to wait --> DEADLOCK
UPDATE accounts SET balance = balance + 50 WHERE id = 1;
COMMIT;
```

#### After (Fix with `SELECT ... FOR UPDATE`):

The logic first acquires all locks in a consistent order (`ORDER BY id`) and then performs the updates.

**Universal Transaction Logic (for both transfers):**
```sql
BEGIN TRANSACTION;

-- Determine the two account IDs involved, e.g., 1 and 2.
-- ALWAYS lock the rows in a consistent order (by ascending ID).
-- This statement forces one transaction to wait until the other
-- has acquired both locks and committed or rolled back.
SELECT id, balance FROM accounts
WHERE id IN (1, 2)
ORDER BY id ASC
FOR UPDATE;

-- Now that we have safely locked the rows, we can perform the updates
-- without risk of deadlock from a similar transaction.
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;

COMMIT;

```
By adding the `SELECT ... FOR UPDATE` with `ORDER BY id`, we guarantee that any transaction attempting to modify accounts 1 and 2 will always try to lock account 1 first, then account 2. This eliminates the circular wait condition and prevents the deadlock.

## 5. System Configuration for Performance

This section details the critical performance-tuning configurations for our primary backend systems. Applying these settings correctly ensures efficient resource usage, reduces latency, and improves overall application stability.

### 5.1 Redis Cache Configuration

Proper memory management in Redis is essential to its function as a high-performance cache. These settings prevent uncontrolled memory growth and ensure that the most relevant data is retained. The configuration is located in `/etc/redis/redis.conf`.

#### Key Directives and Values

*   **`maxmemory`**: This directive constrains the total memory Redis can allocate for user data. It is a critical safeguard against memory exhaustion on the host server. When the limit is reached, Redis begins evicting data according to the `maxmemory-policy`.
    *   **Configured Value**: `maxmemory 2gb`
    *   **Rationale**: Sets a hard limit of 2 gigabytes. This value should be adjusted based on the server's available RAM but must always be set to prevent the OS Out-Of-Memory (OOM) killer from terminating the Redis process.

*   **`maxmemory-policy`**: This defines the algorithm Redis uses to select keys for eviction once the `maxmemory` limit is hit.
    *   **Configured Value**: `maxmemory-policy allkeys-lru`
    *   **Rationale**: The `allkeys-lru` (Least Recently Used) policy evicts the least recently accessed keys from the entire keyspace. This is the ideal strategy for a general-purpose cache, as it prioritizes keeping "hot" or frequently used data in memory. Using a different policy like `noeviction` would cause write commands to fail with an error, defeating the purpose of a self-maintaining cache.

#### Configuration Snippet (`redis.conf`)

The following snippet shows the exact configuration applied in our standard `redis.conf` file.

```ini
################################# MEMORY MANAGEMENT ################################

# Set a memory usage limit to the specified amount of bytes.
# When the memory limit is reached Redis will try to remove keys
# according to the eviction policy selected.
maxmemory 2gb

# How Redis will select what to remove when maxmemory is reached.
# We use allkeys-lru as it best fits our general caching pattern,
# ensuring that the most frequently used items are preserved.
maxmemory-policy allkeys-lru
```

#### Common Issues and Solutions

*   **Error Message**: `(error) OOM command not allowed when used memory > 'maxmemory'.`
    *   **Cause**: This error occurs when `maxmemory-policy` is set to `noeviction` (the default in some older Redis versions) and the memory limit is reached. Redis refuses new write commands to protect existing data.
    *   **Solution**: Change the policy to `allkeys-lru` to enable automatic key eviction and restart the Redis service.

### 5.2 Nginx Gzip Compression

Enabling gzip compression in Nginx reduces the transfer size of text-based assets (like HTML, CSS, and JavaScript) by up to 70-80%. This results in significantly faster client load times and reduced bandwidth costs.

The configuration is added to the `http` block in `/etc/nginx/nginx.conf` for global application.

#### Nginx Configuration Block

This is the complete, production-ready configuration block for enabling and tuning gzip compression.

```nginx
# /etc/nginx/nginx.conf

# --- Gzip Compression Settings ---
# Enables Gzip compression in responses.
gzip on;

# Adds the "Vary: Accept-Encoding" header. This instructs proxies to cache
# separate versions for gzipped and non-gzipped content. Crucial for compatibility.
gzip_vary on;

# Sets the compression level from 1 (fastest, lowest compression) to 9 (slowest, highest).
# Level 6 is the industry-standard balance between CPU usage and compression ratio.
gzip_comp_level 6;

# Do not compress files smaller than 256 bytes. The overhead can make the
# resulting file larger.
gzip_min_length 256;

# Enables compression for requests made through a proxy. 'any' compresses all proxied requests.
gzip_proxied any;

# Specifies the MIME types to compress. 'text/html' is always compressed by default.
# Note: Binaries and images (jpg, png) are omitted as they are already compressed.
# Gzipping them again is wasteful and can increase file size.
gzip_types
    application/atom+xml
    application/javascript
    application/json
    application/ld+json
    application/manifest+json
    application/rss+xml
    application/vnd.ms-fontobject
    application/x-font-ttf
    application/xml
    font/opentype
    image/svg+xml
    image/x-icon
    text/css
    text/plain
    text/x-component;
```

#### Verification Command

You can confirm that gzip is active for a given asset using `curl`.

**Command**:
```bash
curl -H "Accept-Encoding: gzip" -I https://api.your-service.com/styles/main.css
```

**Successful Output**: Look for the `Content-Encoding: gzip` header in the response.

```
HTTP/2 200
server: nginx/1.18.0
date: Wed, 25 Oct 2023 10:30:00 GMT
content-type: text/css
content-length: 12345
vary: Accept-Encoding
content-encoding: gzip   <-- CONFIRMATION
```

If this header is missing, ensure the asset's `Content-Type` is listed in the `gzip_types` directive and its size is greater than the `gzip_min_length` value.

## 6. Architectural Decisions and Rationale

This section outlines the key architectural decisions made during the system's design and evolution, providing the rationale behind each choice. These decisions are foundational to understanding the system's current state, its constraints, and its capabilities.

### 6.1. Retention of Legacy Oracle 8i Database

**Decision:** The legacy Oracle 8i database, `ORA_PROD_01`, which houses core inventory and order data, will be retained and will not be migrated to a modern database platform in the foreseeable future.

**Rationale and Context:**
This decision is not a technical preference but a critical business constraint imposed by an external dependency. Our primary third-party logistics (3PL) partner, **LogiCorp**, uses a legacy warehouse management system (WMS) that interfaces directly with our database.

*   **The Hard Dependency:** The LogiCorp WMS connects to our database using a proprietary and outdated Oracle Call Interface (OCI) driver that is **only compatible with Oracle 8i**. Their system cannot be reconfigured to use modern drivers (like JDBC or newer OCI versions) or connect via an API abstraction layer without a multi-year, multi-million dollar overhaul on their end.

*   **Business Impact of Migration:** Migrating our database off Oracle 8i would sever the connection with LogiCorp's WMS. This would immediately halt all automated inventory updates, order fulfillment, and shipping notifications. The estimated business impact is a complete shutdown of our supply chain, leading to catastrophic revenue loss and reputational damage.

*   **Due Diligence:** We have held multiple discussions with LogiCorp's technical and leadership teams. They have confirmed that there are no plans to upgrade their WMS or its database connectors within their 3-5 year technology roadmap.

*   **Architectural Consequence:** All new services that require access to core inventory or order data must interface with the Oracle 8i database. A dedicated "Legacy Data Access" microservice has been developed to encapsulate the complexity of this interaction and expose data to the rest of the ecosystem via a modern RESTful API. This isolates the legacy dependency and prevents it from propagating across the entire architecture. An attempt to connect a modern Java service using the official Oracle JDBC driver `ojdbc8.jar` will fail with an ORA-28040: No matching authentication protocol error because modern drivers cannot negotiate a session with the 8i database.

**Error Example (When using modern drivers):**
```
java.sql.SQLException: ORA-28040: No matching authentication protocol
    at oracle.jdbc.driver.T4CConnection.logon(T4CConnection.java:492)
    at oracle.jdbc.driver.PhysicalConnection.<init>(PhysicalConnection.java:715)
    ...
```
**Conclusion:** The risk of severe business disruption far outweighs the technical debt and operational overhead of maintaining the Oracle 8i instance. This is a business-driven decision to ensure operational continuity.

---

### 6.2. Adoption of Stateless JWTs for Authentication

**Decision:** Authentication for all user-facing and service-to-service communication is handled using stateless JSON Web Tokens (JWTs).

**Rationale and Context:**
The primary driver for this decision is the requirement for **high scalability and resilience** within our microservices-based architecture. The alternative, stateful session-based authentication, was rejected due to its inherent limitations in a distributed environment.

*   **Problems with Stateful Sessions:** Traditional session management relies on a server-side session store where user data is kept after login. In a distributed system, this leads to two undesirable patterns:
    1.  **Sticky Sessions:** The load balancer must be configured to always route a user's requests to the specific server holding their session data. This creates an availability risk (if the server fails, the session is lost) and complicates load balancing.
    2.  **Centralized Session Store:** A dedicated cache (like Redis or Memcached) is required to store session data, which all service instances can access. While this solves the sticky session problem, it introduces a new network hop for every authenticated request to validate the session, adds another point of failure, and increases infrastructure complexity.

*   **Benefits of Stateless JWTs:**
    1.  **Horizontal Scalability:** A JWT is a self-contained token that carries all the necessary user information (claims) within its payload. Once the token is issued by the authentication service, any microservice can validate it independently by simply verifying its cryptographic signature using a shared public key or secret. This eliminates the need for a shared session store and allows us to add or remove service instances seamlessly. Any server can handle any request.
    2.  **Decoupling:** Services are decoupled from the authentication provider. They only need to know how to validate a token's signature, not how to connect to a session database. This simplifies the microservice design.
    3.  **Performance:** Validation is a fast, local cryptographic operation, avoiding the latency of a database or cache lookup on each API call.

**Example Authentication Flow:**
1.  A user submits their credentials to the `auth-service`.
2.  `auth-service` validates the credentials, generates a JWT, and returns it to the client.
    *   **Sample JWT Payload (Claims):**
        ```json
        {
          "iss": "https://auth.our-app.com",
          "sub": "1138",
          "name": "Jane Doe",
          "email": "jane.doe@example.com",
          "roles": ["user", "inventory-viewer"],
          "exp": 1678886400,
          "iat": 1678885500,
          "jti": "a7b3c9f1-e4d2-4f1a-8c9b-0d1e2f3a4b5c"
        }
        ```
3.  The client stores the JWT and includes it in the `Authorization` header for all subsequent requests to other services.
    *   **Command Example (using cURL):**
        ```bash
        curl -X GET "https://api.our-app.com/v1/inventory/items/SKU123" \
             -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWI..."
        ```
4.  The API Gateway or the receiving microservice (`inventory-service` in this case) retrieves the token, verifies the RS256 signature against the public key, and checks the `exp` (expiration) and `iss` (issuer) claims before processing the request.

**Workaround for Token Revocation:**
A known drawback of stateless tokens is that they cannot be easily revoked before their expiration time. Our solution is a hybrid approach:
*   **Short-Lived Access Tokens:** Access tokens have a short lifespan (e.g., 15 minutes).
*   **Long-Lived Refresh Tokens:** A separate, opaque refresh token with a longer lifespan (e.g., 7 days) is issued alongside the access token. It is stored securely by the client and is used only to request a new access token from the `auth-service` when the old one expires.
*   **Revocation via Refresh Token Blacklist:** To force a user logout or block a compromised account, we only need to invalidate their refresh token in a blacklist maintained by the `auth-service`. The user will be unable to get a new access token, effectively logging them out after the current 15-minute access token expires. This provides a strong balance between security and the high-performance benefits of a stateless architecture.

## 7. Third-Party Integration Pattern: Stripe Payments

This integration pattern outlines the secure and robust method for accepting payments using Stripe's PaymentIntents API. The core principle is a two-phase process: first, an intent to pay is created on the backend, and second, the payment is confirmed on the frontend. This ensures that sensitive payment details (like credit card numbers) never touch our servers, significantly reducing our PCI compliance scope.

The end-to-end flow involves four distinct steps:

1.  **Backend: Create a PaymentIntent.** Our server tells Stripe it wants to collect a specific amount. Stripe returns a `client_secret`.
2.  **Frontend: Receive the `client_secret`**. The frontend requests this secret from our backend.
3.  **Frontend: Confirm the Payment.** The user enters their payment details into a secure UI element provided by Stripe.js. Using the `client_secret`, Stripe.js securely sends this information to Stripe to complete the transaction.
4.  **Backend: Handle the Webhook.** Stripe sends a definitive, secure notification (a webhook) to our server to confirm the payment's success or failure. This is the source of truth for fulfilling the order.

---

### Step 1: Create the PaymentIntent (Backend)

This is the initial server-side step. Its purpose is to register your intention to collect a payment with Stripe.

#### Implementation Details

Create an authenticated API endpoint that the frontend can call to initiate a payment. This endpoint is responsible for communicating with the Stripe API.

**Endpoint Example (`Node.js` with `Express`)**

```javascript
// POST /api/v1/payments/create-intent
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const { getOrderById } = require('../services/orderService');

// This handler assumes the user is authenticated and an orderId is provided.
async function createPaymentIntent(req, res) {
  try {
    const { orderId } = req.body;

    // 1. Validate input
    if (!orderId) {
      return res.status(400).json({ error: 'orderId is required.' });
    }

    // 2. Retrieve order details from your database to get the amount
    const order = await getOrderById(orderId);
    if (!order || order.status === 'PAID') {
      return res.status(404).json({ error: 'Order not found or already paid.' });
    }
    
    // Amount must be in the smallest currency unit (e.g., cents for USD)
    const amountInCents = Math.round(order.totalAmount * 100);

    // 3. Create the PaymentIntent with Stripe
    const paymentIntent = await stripe.paymentIntents.create({
      amount: amountInCents,
      currency: 'usd',
      payment_method_types: ['card'],
      // CRITICAL: Include metadata to link the payment to your internal records.
      // This is essential for webhook reconciliation.
      metadata: { 
        order_id: order.id,
        user_id: req.user.id 
      },
    });

    // 4. Send the client_secret back to the frontend
    res.status(200).json({ 
      clientSecret: paymentIntent.client_secret 
    });

  } catch (error) {
    console.error('[Stripe] Error creating PaymentIntent:', error.message);
    res.status(500).json({ error: 'Internal server error.' });
  }
}
```

#### Key Parameters & Concepts

*   **`STRIPE_SECRET_KEY`**: Your secret API key (e.g., `sk_test_...`). **NEVER** expose this key on the frontend. It must be stored securely as an environment variable on your server.
*   **`amount`**: An integer representing the amount in the currency's smallest unit (e.g., 1000 for $10.00 USD). Do not use floating-point numbers.
*   **`currency`**: A three-letter ISO currency code (e.g., `usd`, `eur`).
*   **`metadata`**: A key-value map for storing your own internal identifiers. This is **not optional** for a robust system. You **must** include your internal `order_id` or equivalent to link the Stripe transaction back to your system during webhook processing.
*   **`client_secret`**: The critical piece of information returned by Stripe. It's a temporary, unique key that grants the frontend permission to confirm this specific payment. It contains the PaymentIntent ID and a secret token.

#### Common Errors and Fixes

*   **Error:** `AuthenticationError: No API key provided.`
    *   **Cause:** The Stripe SDK was not initialized correctly, or `process.env.STRIPE_SECRET_KEY` is undefined.
    *   **Solution:** Ensure your `.env` file is loaded correctly and the `STRIPE_SECRET_KEY` variable is set. Verify that you are using your *secret* key, not your *publishable* key.

*   **Error:** Stripe API returns `400 Bad Request` with message `Invalid integer: 10.99`.
    *   **Cause:** You passed a float for the `amount`.
    *   **Solution:** Convert the amount to cents (or the smallest unit) and ensure it's an integer before passing it to the Stripe API. Use `Math.round(amount * 100)`.

---

### Step 2: Pass the `client_secret` to the Frontend

This is a simple data-fetching step on the client side.

#### Implementation Details

The frontend makes a request to the endpoint created in Step 1.

**Frontend Example (`JavaScript` with `fetch`)**

```javascript
async function initializePayment(orderId) {
  try {
    const response = await fetch('/api/v1/payments/create-intent', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Assuming a JWT token is used for authentication
        'Authorization': `Bearer ${getAuthToken()}` 
      },
      body: JSON.stringify({ orderId: orderId }),
    });

    if (!response.ok) {
        const { error } = await response.json();
        throw new Error(error || 'Failed to initialize payment.');
    }

    const { clientSecret } = await response.json();
    return clientSecret;

  } catch (error) {
    console.error('Failed to fetch client secret:', error);
    // Display an error message to the user
    // e.g., document.getElementById('payment-error').textContent = error.message;
    return null;
  }
}

// Usage:
// const clientSecret = await initializePayment('order_12345');
// if (clientSecret) {
//   // Proceed to Step 3: Mount Stripe Elements and confirm payment
// }
```

---

### Step 3: Confirm the Payment via Stripe.js (Frontend)

The frontend uses the `client_secret` and Stripe's client-side library (`Stripe.js`) to securely collect payment details and confirm the payment.

#### Implementation Details

1.  **Include Stripe.js:** Add the Stripe.js script to your HTML.
    ```html
    <script src="https://js.stripe.com/v3/"></script>
    ```

2.  **Create a Payment Form:** Set up the HTML structure where Stripe's secure inputs (called "Elements") will be mounted.
    ```html
    <form id="payment-form">
      <div id="payment-element">
        <!-- Stripe.js will inject the Payment Element here -->
      </div>
      <button id="submit-button" type="submit">Pay Now</button>
      <div id="payment-message" class="hidden"></div>
    </form>
    ```

3.  **Initialize Stripe.js and Confirm Payment:** Use JavaScript to orchestrate the process.

**Frontend Example (`JavaScript`)**

```javascript
// 1. Initialize Stripe with your PUBLISHABLE key
const stripe = Stripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY);

// Called after fetching the clientSecret from your backend
async function setupPaymentForm(clientSecret) {
  const appearance = { theme: 'stripe' };
  const elements = stripe.elements({ appearance, clientSecret });

  const paymentElement = elements.create('payment');
  paymentElement.mount('#payment-element');

  const form = document.getElementById('payment-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setLoading(true); // Disable form, show spinner

    // 2. Confirm the payment with Stripe
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        // The URL where the customer will be redirected after payment.
        // Stripe appends payment_intent and payment_intent_client_secret GET params.
        return_url: `${window.location.origin}/order/completion`,
      },
    });

    // 3. Handle immediate errors (e.g., card declined)
    // This will only be reached if there is an immediate error. Otherwise, the
    // user is redirected to the `return_url`.
    if (error) {
      if (error.type === "card_error" || error.type === "validation_error") {
        showMessage(error.message);
      } else {
        showMessage("An unexpected error occurred.");
      }
    }
    
    setLoading(false);
  });
}

function showMessage(messageText) {
  const messageContainer = document.querySelector("#payment-message");
  messageContainer.classList.remove("hidden");
  messageContainer.textContent = messageText;
}

function setLoading(isLoading) {
  document.querySelector("#submit-button").disabled = isLoading;
  // Show/hide a loading spinner
}

// --- Tying it all together ---
// const orderId = '...'; 
// initializePayment(orderId).then(clientSecret => {
//   if (clientSecret) {
//     setupPaymentForm(clientSecret);
//   }
// });
```

#### Common Errors and Fixes

*   **Error Message to User:** "Your card was declined."
    *   **Cause:** This is an `error.type` of `card_error` returned from `stripe.confirmPayment`. The issuing bank has declined the transaction.
    *   **Solution:** Gracefully display `error.message` to the user and allow them to try again with a different card. This is expected behavior.

*   **Console Error:** `IntegrationError: You must provide a clientSecret to create a Payment Element.`
    *   **Cause:** `stripe.elements()` was called before the `client_secret` was successfully fetched from your backend.
    *   **Solution:** Ensure your logic awaits the `fetch` call and only initializes Elements after receiving a valid `client_secret`. Add robust null-checking.

---

### Step 4: Handle the Confirmation Webhook (Backend)

This is the most critical step for fulfillment. It is the **only guaranteed** notification of a payment's status. A user could successfully pay but close their browser before being redirected to your `return_url`. Without a webhook, that order would never be fulfilled.

#### Implementation Details

1.  **Create a Webhook Endpoint in your Stripe Dashboard:**
    *   Go to Developers -> Webhooks -> Add endpoint.
    *   **Endpoint URL:** `https://your-domain.com/api/v1/stripe-webhook`
    *   **Events to listen to:** At a minimum, select `payment_intent.succeeded` and `payment_intent.payment_failed`.
    *   After creation, Stripe will provide a **Webhook signing secret** (e.g., `whsec_...`). Store this in your environment variables.

2.  **Create the Webhook Handler on the Backend:**

**Endpoint Example (`Node.js` with `Express`)**

```javascript
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const { fulfillOrder, failOrder } = require('../services/orderService');

// IMPORTANT: You need the raw request body for signature verification.
// Express's default json parser will corrupt it.
// Use this middleware BEFORE your json parser for this specific endpoint.
const webhookHandler = (req, res) => {
  const sig = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  let event;

  try {
    // 1. Verify the event came from Stripe
    event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
  } catch (err) {
    console.warn(`[Stripe Webhook] Signature verification failed:`, err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  const paymentIntent = event.data.object;

  // 2. Handle the event type
  switch (event.type) {
    case 'payment_intent.succeeded':
      console.log(`[Stripe Webhook] PaymentIntent ${paymentIntent.id} succeeded.`);
      
      // Use the metadata to find your internal order
      const orderId = paymentIntent.metadata.order_id;
      if (!orderId) {
        console.error(`[Stripe Webhook] CRITICAL: Missing order_id in metadata for PaymentIntent ${paymentIntent.id}`);
        break; // Acknowledge the event to Stripe but log the error
      }
      
      // Fulfill the purchase (e.g., update DB, send email, ship goods)
      // This function should be idempotent!
      fulfillOrder(orderId, paymentIntent.id);
      break;

    case 'payment_intent.payment_failed':
      console.log(`[Stripe Webhook] PaymentIntent ${paymentIntent.id} failed.`);
      const failedOrderId = paymentIntent.metadata.order_id;
      // Optional: Update DB, notify user of failure
      failOrder(failedOrderId, paymentIntent.last_payment_error?.message);
      break;

    default:
      // Unexpected event type
      console.warn(`[Stripe Webhook] Unhandled event type: ${event.type}`);
  }

  // 3. Acknowledge receipt of the event to Stripe
  res.status(200).json({ received: true });
};

// In your router setup:
// app.post('/api/v1/stripe-webhook', express.raw({type: 'application/json'}), webhookHandler);
```

#### Key Concepts and Fixes

*   **Signature Verification:** **This is mandatory.** It prevents attackers from sending fake webhooks to your endpoint. The `stripe.webhooks.constructEvent` function compares the signature Stripe sends in the `stripe-signature` header with one it generates using the raw request body and your webhook secret.
*   **Problem:** Signature verification always fails, even with the correct secret.
    *   **Cause:** `express.json()` or another body-parser middleware has already parsed and modified the request body before it reaches the `constructEvent` function. The function requires the untouched, raw body buffer.
    *   **Fix:** As shown in the code comment, use `express.raw({type: 'application/json'})` as the middleware for *only* the webhook route. Ensure this raw body parser runs *before* any global JSON parser.
*   **Idempotency:** Your fulfillment logic (`fulfillOrder`) might be called multiple times for the same event if Stripe retries. Design your logic to handle this safely. For example, check if the order status is already 'PAID' before trying to update the database or send an email again.
*   **Response to Stripe:** You **must** return a `2xx` status code to Stripe quickly. If Stripe doesn't receive a `200 OK` response, it will consider the webhook delivery a failure and will retry sending it, leading to duplicate processing. Perform any long-running tasks (like sending emails) asynchronously after sending the response.

## 8. Appendix: Command and Configuration Reference

### Java Application Startup

This command starts the Java application, sets the initial and maximum heap sizes to 2GB, and activates the `production` Spring profile.

```bash
java -Xms2048m -Xmx2048m -Dspring.profiles.active=production -jar your-application-name.jar
```

*   `-Xms2048m`: Sets the initial Java heap size to 2048 megabytes. Setting this to the same value as `-Xmx` can prevent heap resizing pauses during startup and runtime.
*   `-Xmx2048m`: Sets the maximum Java heap size to 2048 megabytes. This is the most critical memory setting to prevent `java.lang.OutOfMemoryError`.
*   `-Dspring.profiles.active=production`: Activates Spring Boot's `production` profile, loading `application-production.properties`.
*   `-jar your-application-name.jar`: Specifies the executable JAR file to run.

---

### Redis Configuration (`redis.conf`)

These are the key configuration lines for setting up Redis as a high-performance cache. This configuration sets a memory limit, defines an eviction policy, and disables RDB persistence to avoid disk I/O latency.

```ini
# redis.conf

# 1. Set a memory limit. Replace '2gb' with your desired limit.
# If the memory limit is reached, Redis will start evicting keys
# based on the maxmemory-policy.
maxmemory 2gb

# 2. Set the eviction policy to 'allkeys-lru'.
# This policy evicts the least recently used (LRU) keys first when
# the 'maxmemory' limit is reached. It is a good general-purpose choice.
# Other options include 'volatile-lru', 'allkeys-random', etc.
maxmemory-policy allkeys-lru

# 3. Disable RDB persistence for pure cache usage.
# This prevents Redis from blocking to write snapshots to disk.
# Comment out all 'save' lines and add 'save ""' to explicitly disable it.
#
# save 900 1
# save 300 10
# save 60 10000
save ""
```

---

### Nginx Location Block

This Nginx `location` block configures a reverse proxy to a backend application. It includes comprehensive CORS headers to allow cross-origin requests and enables Gzip compression to reduce payload size for common web asset types.

```nginx
# /etc/nginx/sites-available/default

# Assumes an upstream block is defined, e.g.:
# upstream backend_app {
#   server 127.0.0.1:8080;
# }

location /api/ {
    # --- PROXY --- #
    # Forward requests to the backend application server
    proxy_pass http://backend_app/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Connection "";

    # --- GZIP COMPRESSION --- #
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        application/json
        application/javascript
        application/rss+xml
        application/atom+xml
        image/svg+xml;

    # --- CORS HEADERS --- #
    # Handle pre-flight OPTIONS requests
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' "$http_origin" always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Origin, Accept, X-Requested-With' always;
        add_header 'Access-Control-Max-Age' 1728000; # 20 days
        add_header 'Content-Type' 'text/plain; charset=utf-8';
        add_header 'Content-Length' 0;
        return 204;
    }

    # Add CORS headers to actual requests
    add_header 'Access-Control-Allow-Origin' "$http_origin" always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Origin, Accept, X-Requested-With' always;
}
```

---

### SQL Deadlock Prevention

To fix deadlocks occurring during a "read-then-write" sequence, use a `SELECT ... FOR UPDATE` statement within a transaction. This acquires a row-level lock on the selected rows, preventing other transactions from modifying them until the current transaction is committed or rolled back.

**Example Scenario**: Two concurrent requests try to read and then update a user's account balance.

**Problematic SQL (Prone to Deadlock):**
```sql
-- Transaction 1
BEGIN;
-- Reads current balance
SELECT balance FROM accounts WHERE user_id = 123;
-- business logic calculates new balance...
UPDATE accounts SET balance = 950 WHERE user_id = 123;
COMMIT;

-- Transaction 2 (concurrent)
BEGIN;
-- Reads current balance
SELECT balance FROM accounts WHERE user_id = 123;
-- business logic calculates new balance...
UPDATE accounts SET balance = 1050 WHERE user_id = 123; -- This may deadlock with Tx1's update
COMMIT;
```

**Solution with `FOR UPDATE`:**
This ensures that the first transaction to select the row locks it, forcing the second transaction to wait until the first is complete.

```sql
-- This entire block should be executed as a single transaction
BEGIN;

-- Select the user's account row and lock it immediately.
-- Any other transaction trying to select this same row FOR UPDATE
-- or trying to UPDATE/DELETE it will be blocked until this transaction ends.
SELECT balance
FROM accounts
WHERE user_id = 123
FOR UPDATE;

-- After the lock is acquired, it's safe to perform business logic
-- and then update the row without race conditions or deadlocks.
-- Example: update the balance based on the value read above.
UPDATE accounts
SET balance = 950
WHERE user_id = 123;

-- Commit the transaction to release the lock.
COMMIT;
```