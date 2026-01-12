# Configuration Principles Cluster

**Load when**: Managing secrets, environment variables, external service integrations, Doppler configuration

**Principles**: #13, #24

**Related**: [Doppler Config Guide](../../docs/deployment/DOPPLER_CONFIG.md)

---

## Principle #13: Secret Management Discipline

Use Doppler for centralized secret management with config inheritance. Cross-environment inheritance (dev → local_dev) syncs shared secrets while allowing local overrides. Validate secrets at application startup (fail-fast).

**Config organization**:
```
dev (root, AWS)
  └── local_dev (inherits from dev, local overrides)
stg (root, AWS)
prd (root, AWS)
```

**Doppler constraints**:
- Same-environment inheritance **forbidden**
- Environment-prefixed naming **required** (e.g., `local_*` for local environment)
- Cross-environment inheritance **allowed** (local_dev can inherit from dev)

**Benefits**:
- No secret duplication (inherits from parent)
- Automatic propagation (update dev → local_dev gets it)
- Clear environment separation

**Anti-patterns**:
- ❌ Duplicating secrets across configs (breaks single source of truth)
- ❌ Same-environment inheritance (violates Doppler constraint)
- ❌ Manual secret sync (error-prone, causes drift)

See [Doppler Config Guide](../../docs/deployment/DOPPLER_CONFIG.md) for setup workflows, inheritance patterns, and troubleshooting.

---

## Principle #24: External Service Credential Isolation

External services with **webhook-based integrations** require **per-environment credentials**. Copying credentials across environments creates silent routing failures where operations succeed technically but fail functionally.

**Why webhooks require isolation**: LINE, Telegram, Slack webhooks are per-channel/per-bot. Using dev credentials in staging means staging Lambda replies via dev channel—user receives nothing, but Lambda returns 200.

**Isolation checklist for new environments**:
1. Create new channel/bot/app in external service
2. Generate new credentials for that channel
3. Configure webhook URL to point to new environment
4. Store credentials in Doppler under environment-specific config
5. Verify end-to-end: user action → webhook → Lambda → reply → **user receives**

**Services requiring isolation**:
- LINE (channel per environment)
- Telegram (bot per environment)
- Slack (app per environment)
- Discord (bot per environment)
- Stripe webhooks (endpoint per environment)
- GitHub Apps (installation per environment)
- OAuth providers (client per environment)

**Verification**: HTTP 200 is Layer 1 evidence (weakest). External services require **Layer 4 ground truth**—user actually receives the message.

**Anti-patterns**:
- ❌ Copying dev credentials to staging "to test quickly"
- ❌ Sharing webhook channels across environments
- ❌ Assuming HTTP 200 from SDK = message delivered

See [External Service Credential Isolation Guide](../../docs/guides/external-service-credential-isolation.md).

---

## Quick Checklist

New environment setup:
- [ ] Create Doppler config with inheritance (if applicable)
- [ ] Create separate channel/bot for external services
- [ ] Configure webhook URLs for new environment
- [ ] Store credentials in Doppler (not GitHub secrets)
- [ ] Verify end-to-end (user receives message)

Secret management:
- [ ] All secrets in Doppler (not code, not .env)
- [ ] Inheritance configured for shared secrets
- [ ] Environment-specific overrides in child config
- [ ] Startup validation for required secrets

---

*Cluster: configuration-principles*
*Last updated: 2026-01-12*
