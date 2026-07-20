# Technical Security Policy

## Secret Management

API keys and credentials must be stored in environment variables and excluded from version control. Secrets must never appear in logs, reports, or API error responses.

## File-System Restrictions

Agent-generated files may only be written inside approved directories. User-supplied filenames must be sanitized and validated before use.

## Input Validation

Empty, excessively long, or overly broad research objectives must be rejected. API requests must be validated using typed schemas.

## Error Handling

External failures should return controlled error messages. Internal stack traces and sensitive configuration values must not be exposed to API clients.
