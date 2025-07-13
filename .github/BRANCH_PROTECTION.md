# Branch Protection Setup

This document explains how to configure branch protection rules to enforce code quality checks before merging PRs.

## Required Status Checks

The following checks are **required** for all PRs to the `main` branch:

> **Note**: This repo uses a simple workflow with short-lived feature branches merging directly to `main`. CI runs only on pull requests.

### 🔒 Required Checks
- **Lint and Format Check** - Black formatting and Ruff linting
- **Unit Tests** - Unit tests on Python 3.11 (matches production)
- **Integration Tests** - Full system integration tests
- **Docker Build Test** - Ensures Docker builds successfully

### ℹ️ Informational Checks
- **Security Analysis** - Runs separately with Bandit, Safety, Semgrep, and CodeQL (not required for PR merge)

## Setting Up Branch Protection

### Automatic Setup (Recommended)

Use the GitHub CLI to set up branch protection rules automatically:

```bash
# Set up branch protection for main branch
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Lint and Format Check","Unit Tests","Integration Tests","Docker Build Test"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field restrictions=null

# Set up branch protection for develop branch  
gh api repos/:owner/:repo/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Lint and Format Check","Unit Tests","Integration Tests","Docker Build Test"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field restrictions=null
```

### Manual Setup via GitHub UI

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Branches**
3. Click **Add rule** or edit existing rule for `main` branch

#### Branch protection settings:
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: `1`
  - ✅ Dismiss stale PR approvals when new commits are pushed
  - ❌ Require review from code owners (optional)

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - ✅ Required status checks:
    - `Lint and Format Check`
    - `Unit Tests`
    - `Integration Tests`
    - `Docker Build Test`

- ✅ **Require conversation resolution before merging**
- ✅ **Restrict pushes that create files** (optional)
- ✅ **Do not allow bypassing the above settings** (recommended)

4. This repo only uses `main` branch protection (no `develop` branch)

## What This Enforces

### ✅ Code Quality Standards
- All code must pass Black formatting checks
- All code must pass Ruff linting (style, bugs, complexity)
- No new security vulnerabilities (Bandit + Safety)

### ✅ Testing Requirements  
- Unit tests must pass on Python 3.9, 3.11, and 3.12
- Test coverage is tracked and reported
- No broken tests allowed in main branches

### ✅ Build Verification
- Docker images must build successfully
- No build-breaking changes allowed

### ✅ Review Process
- At least 1 approving review required
- Stale approvals dismissed when new commits pushed
- All conversations must be resolved

## Developer Workflow

### For Contributors

1. **Create feature branch** from `main`
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature
   ```

2. **Develop with pre-commit hooks**
   ```bash
   # Install hooks (one-time)
   make pre-commit-install
   
   # Develop and commit (hooks run automatically)
   git add .
   git commit -m "feat: your feature"
   ```

3. **Run local checks before pushing**
   ```bash
   # Run same checks as CI
   make lint
   make test-unit
   
   # Or use the lint script
   ./scripts/lint.sh
   ```

4. **Create PR and wait for checks**
   - PR checks run automatically
   - Fix any failing checks
   - Request review once all checks pass

### For Maintainers

1. **Review PR when all checks pass**
   - All required status checks must be green ✅
   - Code review for logic, design, documentation
   - Approve when satisfied

2. **Merge strategies**
   - **Squash and merge** (recommended for features)
   - **Merge commit** (for releases)
   - **Rebase and merge** (for clean history)

## Troubleshooting

### Common Issues

**❌ "Code Quality (Required)" failing**
```bash
# Fix formatting
black .
git add . && git commit -m "style: fix formatting"

# Fix linting issues  
ruff check --fix .
git add . && git commit -m "style: fix linting"
```

**❌ "Unit Tests (Required)" failing**
```bash
# Run tests locally to debug
make test-unit

# Fix issues and commit
git add . && git commit -m "fix: resolve test failures"
```

**❌ "Security Check (Required)" failing**
```bash
# Check security issues
bandit -r mcp_server cli
safety check

# Fix vulnerabilities and commit
git add . && git commit -m "security: fix vulnerabilities"
```

**❌ "Docker Build (Required)" failing**
```bash
# Test Docker build locally
docker compose build

# Fix Dockerfile issues and commit
git add . && git commit -m "fix: docker build issues"
```

### Bypassing Checks (Emergency Only)

Repository admins can bypass branch protection in emergencies:
1. Go to **Settings** → **Branches**
2. Temporarily uncheck **Do not allow bypassing the above settings**
3. Merge the urgent fix
4. **Immediately re-enable protection**
5. Create follow-up PR to fix any quality issues

## Benefits

✅ **Consistent Quality** - All code meets minimum quality standards
✅ **Automated Enforcement** - No manual verification needed
✅ **Early Issue Detection** - Problems caught before merge
✅ **Team Productivity** - Less time debugging production issues
✅ **Documentation** - Clear expectations for contributors
