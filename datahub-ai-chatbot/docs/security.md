# Security Guide

## Authentication

| Mode   | Description                        | Use Case          |
|--------|------------------------------------|-------------------|
| mock   | Hardcoded developer identity       | Local development |
| header | User info from HTTP headers        | Staging / behind gateway |
| jwt    | JWT Bearer token validation        | Production        |

### Configuration

```env
AUTH_MODE=jwt
AUTH_REQUIRED=true
JWT_SECRET_KEY=<strong-random-secret>
```

## Authorization

- All entity access goes through `AuthorizationService.can_view_entity`
- Admin users bypass all checks
- Deny rules take priority over allow rules
- Tenant isolation enforced before allow/deny
- Unauthorized chunks are filtered before LLM context assembly

## SSRF Protection

The `SSRFGuard` blocks:

- `file://` and `ftp://` protocols
- `localhost`, `127.0.0.1`, `0.0.0.0`
- Private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Link-local addresses (169.254.x)
- Cloud metadata endpoints
- URLs with embedded credentials

### Configuration

```env
DOCUMENT_ALLOWED_DOMAINS=docs.example.com,assets.example.com
MAX_REDIRECTS=5
```

## API Security

### Rate Limiting

```env
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
```

### Security Headers (set by Nginx)

- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: default-src 'self'`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

### Input Validation

- All API inputs validated by Pydantic schemas
- File uploads restricted by MIME type allowlist
- Document size limited to `MAX_DOCUMENT_SIZE_MB`
- URLs validated before download

## Secrets Management

### Local Development

Use `.env` file (gitignored):

```env
DATAHUB_TOKEN=
JWT_SECRET_KEY=dev-secret
FIREWORKS_API_KEY=
OPENAI_API_KEY=
```

### Docker

Use Docker secrets or environment variables:

```yaml
secrets:
  datahub_token:
    file: ./secrets/datahub_token.txt
```

### Kubernetes

Use Kubernetes Secrets (never in ConfigMap):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: chatbot-secret
type: Opaque
data:
  DATAHUB_TOKEN: <base64>
  JWT_SECRET_KEY: <base64>
```

### External Secret Manager (Production)

For production, use:

- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager

## Audit Logging

- All authorization decisions are logged
- Access tokens and sensitive prompts are never logged
- Audit events include: action, resource, decision, reason
- Audit logs are stored in `audit_logs` table

## Container Security

### Dockerfile Best Practices

- Multi-stage builds
- Non-root user (`appuser`)
- Read-only root filesystem
- Dropped Linux capabilities
- No debug tools in production image
- Healthcheck configured

### Pod Security Context (Kubernetes)

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
```

### Container Security Context

```yaml
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  readOnlyRootFilesystem: true
  runAsNonRoot: true
```

## Network Security

- Network policies restrict egress to only required services
- PostgreSQL, Redis, and OpenSearch are not exposed externally
- Metrics endpoint is internal-only
- Ingress terminates TLS

## Dependency Security

Regularly scan dependencies:

```bash
# Check for known vulnerabilities
pip-audit

# Scan Docker images
trivy image registry.example.com/datahub-ai-chatbot:latest

# Scan Kubernetes manifests
kube-score score deploy/*.yaml
```

## Penetration Testing Checklist

- [ ] Authentication bypass
- [ ] JWT token forgery
- [ ] SSRF via document URL
- [ ] Path traversal in file storage
- [ ] SQL injection via search
- [ ] XSS via chatbot responses
- [ ] Unauthorized data access via ACL bypass
- [ ] Rate limiting bypass
- [ ] Secret exposure in logs
- [ ] Container escape via mounted volumes
