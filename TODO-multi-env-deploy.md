# Multi-Environment Deployment TODO

## Current State
- [x] dev deployed: `https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com`
- [ ] staging: not deployed
- [ ] prod: not deployed

## Implementation Order

### Phase A: Staging Setup
- [ ] 1. Deploy staging infrastructure (Terraform with staging.tfvars)
- [ ] 2. Deploy staging app (backend + frontend)
- [ ] 3. Run automated tests on dev
- [ ] 4. Run automated tests on staging
- [ ] 5. Manual test dev
- [ ] 6. Manual test staging

### Phase B: Production Setup
- [ ] 7. Deploy prod infrastructure (Terraform with prod.tfvars)
- [ ] 8. Deploy prod app (backend + frontend)
- [ ] 9. Run automated tests on prod
- [ ] 10. Manual test prod

## Commands Reference

### Deploy Staging Infrastructure
```bash
cd terraform
cat > staging.tfvars << 'EOF'
environment = "staging"
EOF
terraform plan -var-file=staging.tfvars -out=staging.tfplan
terraform apply staging.tfplan
```

### Deploy Prod Infrastructure
```bash
cd terraform
cat > prod.tfvars << 'EOF'
environment = "prod"
EOF
terraform plan -var-file=prod.tfvars -out=prod.tfplan
terraform apply prod.tfplan
```

### Deploy Application
```bash
just deploy-telegram-backend staging
just deploy-telegram-frontend staging

just deploy-telegram-backend prod
just deploy-telegram-frontend prod
```

### Run Automated Tests
```bash
# Dev
TELEGRAM_API_URL=https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com \
  pytest tests/test_smoke.py -v

# Staging (replace URL after deploy)
TELEGRAM_API_URL=<staging-api-url> pytest tests/test_smoke.py -v

# Prod (replace URL after deploy)
TELEGRAM_API_URL=<prod-api-url> pytest tests/test_smoke.py -v
```

## Manual Testing Checklist

For each environment (dev → staging → prod):

- [ ] Open webapp URL in browser (no console errors)
- [ ] Search for "NVDA" (autocomplete works)
- [ ] Click ticker result (report generation starts)
- [ ] Wait for report (full report with charts)
- [ ] Add to watchlist (persists on refresh)
- [ ] Remove from watchlist
- [ ] View rankings (all 4 tabs work)
- [ ] Check mobile responsiveness

---

## Enhancements (Post-Launch)

### CI/CD Multi-Environment Support
**Priority:** High after manual validation

- [ ] Add environment matrix or separate jobs in `.github/workflows/deploy.yml`
- [ ] Use GitHub environments for staging/prod approval gates
- [ ] Update function names to use environment suffix dynamically

---

## Optional Features (Future Iterations)

### 1. Frontend Build Process
**Effort:** 2-3 hours | **Priority:** Medium

- [ ] Add Vite/Webpack for JavaScript minification & bundling
- [ ] CSS minification
- [ ] Asset fingerprinting (cache busting)
- [ ] Tree shaking

### 2. PWA Support
**Effort:** 3-4 hours | **Priority:** Low

- [ ] Service worker for offline caching
- [ ] App manifest for "Add to Home Screen"
- [ ] Background sync for watchlist updates

### 3. Accessibility (a11y)
**Effort:** 2-3 hours | **Priority:** Medium

- [ ] ARIA labels for screen readers
- [ ] Keyboard navigation support
- [ ] Focus indicators
- [ ] Color contrast improvements

### 4. Frontend E2E Tests
**Effort:** 4-6 hours | **Priority:** Medium

- [ ] Playwright test suite
- [ ] Test critical user flows:
  - [ ] Search → Report
  - [ ] Watchlist CRUD
  - [ ] Rankings navigation

### 5. Price Alert Notifications
**Effort:** 1-2 days | **Priority:** Low

- [ ] Telegram Bot push notifications
- [ ] Price threshold triggers
- [ ] DynamoDB for alert storage

### 6. Portfolio Tracking
**Effort:** 2-3 days | **Priority:** Low

- [ ] Holdings management
- [ ] P&L calculation
- [ ] Performance charts

### 7. Multi-language (i18n)
**Effort:** 1 day | **Priority:** Low

- [ ] Thai/English toggle
- [ ] i18n library integration
- [ ] Translated UI strings

---

## Research Notes

(Add your research notes here)
