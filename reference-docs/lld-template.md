# Low Level Design (LLD) Template

## Component: [Component Name]

### 1. Overview
[1 paragraph describing this component's purpose and responsibilities]

### 2. API / Interface Contracts

#### REST Endpoints
| Method | Path | Auth | Request Body | Response | Status Codes |
|--------|------|------|-------------|----------|-------------|
| POST | /api/resource | JWT | `{field: type}` | `{id, field}` | 201, 400, 401 |
| GET | /api/resource/:id | JWT | - | `{id, field}` | 200, 401, 404 |

#### Request Schema
```json
{
  "field_name": "string (required, max 255)",
  "other_field": "integer (optional, default: 0)"
}
```

#### Response Schema
```json
{
  "id": "uuid",
  "field_name": "string",
  "created_at": "ISO8601 timestamp"
}
```

### 3. Data Models

#### Database Table / DynamoDB Schema
```
TableName: resource_table
  PK: id (UUID, string)
  SK: created_at (timestamp, number)
  Attributes:
    field_name: string
    status: ENUM(active, inactive, deleted)
    user_id: string (FK reference)
    ttl: number (epoch, for auto-deletion)
  GSI:
    user-index: PK=user_id, SK=created_at
```

### 4. Key Sequences

#### Happy Path: [Action Name]
```
Client                 Service           Database
  |                       |                  |
  |-- POST /api/resource ->|                  |
  |                       |-- validate JWT   |
  |                       |-- validate body  |
  |                       |-- PutItem ------>|
  |                       |<-- 200 OK -------|
  |<-- 201 Created --------|
```

#### Error Path: [Validation Failure]
```
Client                 Service
  |                       |
  |-- POST /api/resource ->|
  |                       |-- validate body (FAIL)
  |<-- 400 Bad Request ----|
  |   {"error": "field_name is required"}
```

### 5. Business Logic

#### Validation Rules
- `field_name`: required, non-empty, max 255 chars
- `status`: must be one of: active, inactive
- User must own the resource to update/delete

#### Processing Rules
1. [Rule 1 description]
2. [Rule 2 description]

### 6. Error Handling
| Error Condition | HTTP Code | Response Body | Recovery |
|----------------|-----------|---------------|----------|
| Missing JWT | 401 | `{"detail": "Missing token"}` | Client re-authenticates |
| Invalid JWT | 401 | `{"detail": "Invalid token"}` | Client re-authenticates |
| Not found | 404 | `{"detail": "Resource not found"}` | Client handles |
| Validation error | 400 | `{"detail": "field errors..."}` | Client corrects input |
| Internal error | 500 | `{"detail": "Internal error"}` | Retry with backoff |

### 7. Configuration
| Env Variable | Purpose | Default | Required |
|-------------|---------|---------|----------|
| AWS_REGION | AWS region | us-east-1 | Yes |
| TABLE_NAME | DynamoDB table | - | Yes |
| LOG_LEVEL | Logging verbosity | INFO | No |

### 8. Performance Considerations
- Query uses GSI to avoid full table scan
- Response cached for 60s where data is not user-specific
- Pagination: max 50 items per page
