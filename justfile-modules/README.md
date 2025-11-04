# Justfile Modules

This project uses a modular justfile structure for better organization and maintainability.

## Structure

```
justfile                      # Main entry point
justfile-modules/
├── webapp.just              # Web application commands
├── test.just                # Testing commands
├── deps.just                # Dependency management
├── db.just                  # Database operations
├── reports.just             # Report generation
├── dev.just                 # Development tools
├── deploy.just              # Deployment commands
├── api.just                 # API testing
├── utils.just               # Utility commands
├── docs.just                # Documentation commands
└── workflow.just            # Development workflow
```

## Module Descriptions

### webapp.just
Web application commands:
- `webapp` - Start Flask webapp
- `webapp-dev` - Start in development mode
- `server` - Start server
- `check-webapp` - Check if app is running
- `open-tiles` - Open tiles page in browser

### test.just
Testing commands:
- `test` - Run all tests
- `test-unit` - Run unit tests only
- `test-e2e` - Run E2E tests
- `test-e2e-headed` - Run E2E tests with UI
- `test-file FILE` - Run specific test file
- `test-cov` - Run tests with coverage

### deps.just
Dependency management:
- `install` - Install all dependencies
- `install-minimal` - Install minimal dependencies
- `install-playwright` - Install Playwright browsers
- `update` - Update dependencies

### db.just
Database operations:
- `db-init` - Initialize database
- `db-index-pdfs` - Index existing PDFs
- `db-check` - Check database contents
- `db-view` - View database tables
- `reset-db` - Reset database and reindex

### reports.just
Report generation:
- `report TICKER` - Generate report for ticker
- `reports-all` - Generate all reports
- `reports-faithful` - Generate with faithfulness scoring

### dev.just
Development tools:
- `lint` - Run linter
- `format` - Format code
- `complexity` - Analyze code complexity
- `clean` - Clean cache files

### deploy.just
Deployment commands:
- `deploy-lambda` - Create Lambda deployment
- `deploy-lambda-minimal` - Create minimal Lambda deployment
- `deploy` - Deploy to Lambda

### api.just
API testing:
- `api-test` - Test API endpoint
- `api-tiles` - Test tiles API

### utils.just
Utility commands:
- `quick-test TICKER` - Quick test for ticker
- `test-audio` - Test audio generation
- `test-botnoi` - Test Botnoi integration
- `scores` - Show scores

### docs.just
Documentation commands:
- `docs-api` - View API documentation
- `docs-quickstart` - View quickstart guide

### workflow.just
Development workflow:
- `dev-start` - Start full dev environment
- `dev-stop` - Stop dev environment

## Usage

All commands work the same as before:

```bash
# Commands from any module are available
just webapp
just test
just report DBS19
just dev-start
```

## Adding New Commands

1. Identify the appropriate module
2. Add the command to that module file
3. The command will be automatically available in the main justfile

## Benefits

- **Organization**: Commands grouped by functionality
- **Maintainability**: Easier to find and modify commands
- **Scalability**: Easy to add new modules or commands
- **Clarity**: Each module has a clear purpose
