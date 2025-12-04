# API Guidelines

Standards for building APIs in this project.

## REST Conventions
- Use plural nouns for resources: `/api/users`, `/api/profiles`
- Use HTTP methods correctly: GET (read), POST (create), PUT (update), DELETE (remove)
- Return appropriate status codes: 200, 201, 400, 404, 500

## Response Format
```json
{
  "data": { ... },
  "error": null
}
```

## Error Handling
- Always return structured error responses
- Include error codes for programmatic handling
- Provide human-readable messages
