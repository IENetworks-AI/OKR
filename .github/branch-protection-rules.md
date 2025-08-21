# Branch Protection Rules - OKR Project

## Overview

This document outlines the branch protection rules and access controls for the OKR project repository. These rules ensure code quality, security, and proper deployment procedures.

## 🛡️ Main Branch Protection

### Access Control
- **Repository Owners Only**: Only repository owners can merge to the `main` branch
- **No Direct Pushes**: Direct pushes to `main` are blocked for all users
- **Pull Request Required**: All changes must go through pull requests
- **Branch Deletion Protection**: The `main` branch cannot be deleted

### Required Status Checks
Before merging to `main`, the following checks must pass:

1. **Code Quality Checks**
   - Code formatting (Black)
   - Linting (Flake8)
   - Type checking (mypy)

2. **Security Scans**
   - Bandit security scan
   - Dependency vulnerability scan
   - Secrets detection

3. **Testing**
   - Unit tests (pytest)
   - Integration tests
   - ETL pipeline validation

4. **Build Verification**
   - Docker build tests
   - Docker Compose validation
   - Configuration file validation

5. **Deployment Validation**
   - Oracle deployment configuration check
   - Service configuration validation
   - Environment variable validation

### Pull Request Requirements

#### Required Reviews
- **Minimum Reviews**: 2 approvals required
- **Reviewers**: Must include at least one repository owner
- **Dismissal**: Stale reviews are dismissed when new commits are pushed

#### Required Status Checks
- All status checks must pass before merging
- Status checks must be up to date with the latest commit
- No merge conflicts allowed

#### Branch Restrictions
- **Source Branch**: Must be up to date with `main`
- **Target Branch**: Only `main` branch
- **Merge Strategy**: Squash and merge preferred

## 🔄 Branch Strategy

### Branch Types

#### 1. Main Branch (`main`)
- **Purpose**: Production-ready code
- **Access**: Repository owners only
- **Deployment**: Triggers Oracle server deployment
- **Protection**: Full protection enabled

#### 2. Develop Branch (`develop`)
- **Purpose**: Integration branch for features
- **Access**: All contributors
- **Deployment**: No deployment
- **Protection**: Medium protection

#### 3. Test Branch (`test`)
- **Purpose**: Staging and testing
- **Access**: All contributors
- **Deployment**: Test environment deployment
- **Protection**: Medium protection

#### 4. Feature Branches (`feature/*`)
- **Purpose**: Individual feature development
- **Access**: Feature developer
- **Deployment**: No deployment
- **Protection**: No protection

#### 5. Hotfix Branches (`hotfix/*`)
- **Purpose**: Critical bug fixes
- **Access**: Repository owners only
- **Deployment**: Emergency deployment
- **Protection**: High protection

### Branch Naming Convention

```
feature/etl-enhancement     # New ETL features
feature/api-improvement     # API improvements
feature/kafka-integration   # Kafka integration
hotfix/critical-bug         # Critical bug fixes
hotfix/security-patch       # Security patches
```

## 🔐 Access Control Matrix

| Role | Main | Develop | Test | Feature | Hotfix |
|------|------|---------|------|---------|--------|
| Repository Owner | ✅ Merge | ✅ Merge | ✅ Merge | ✅ All | ✅ All |
| Maintainer | ❌ Merge | ✅ Merge | ✅ Merge | ✅ All | ❌ Merge |
| Contributor | ❌ Merge | ✅ Merge | ✅ Merge | ✅ All | ❌ All |

## 📋 Workflow Rules

### Feature Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Development**
   ```bash
   # Make changes
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**
   - Target: `develop` branch
   - Include description of changes
   - Link related issues
   - Request reviews

4. **Code Review**
   - Address review comments
   - Update branch if needed
   - Ensure all checks pass

5. **Merge to Develop**
   - Squash and merge
   - Delete feature branch

### Release Workflow

1. **Merge to Test**
   ```bash
   git checkout test
   git merge develop
   git push origin test
   ```

2. **Testing**
   - Automated tests run
   - Manual testing in test environment
   - Performance validation

3. **Merge to Main** (Repository Owner Only)
   ```bash
   git checkout main
   git merge develop
   git push origin main
   ```

4. **Deployment**
   - Automated deployment to Oracle server
   - Production validation
   - Monitoring activation

### Hotfix Workflow

1. **Create Hotfix Branch** (Repository Owner Only)
   ```bash
   git checkout main
   git checkout -b hotfix/critical-issue
   ```

2. **Fix and Test**
   ```bash
   # Make critical fix
   git add .
   git commit -m "hotfix: fix critical issue"
   git push origin hotfix/critical-issue
   ```

3. **Emergency Deployment**
   - Create pull request to main
   - Expedited review process
   - Immediate deployment after approval

## 🚨 Emergency Procedures

### Bypass Protection (Repository Owner Only)

In emergency situations, repository owners can:

1. **Temporarily Disable Protection**
   - Go to repository settings
   - Disable branch protection rules
   - Make emergency changes
   - Re-enable protection

2. **Force Push** (Last Resort)
   ```bash
   git push --force-with-lease origin main
   ```

3. **Emergency Rollback**
   ```bash
   git revert HEAD
   git push origin main
   ```

### Emergency Contact

For emergency situations:
- **Primary**: Repository owner
- **Secondary**: Maintainers
- **Escalation**: Project lead

## 📊 Monitoring and Compliance

### Branch Protection Monitoring

- **Daily**: Check for bypassed protections
- **Weekly**: Review access logs
- **Monthly**: Audit branch protection effectiveness

### Compliance Checks

- [ ] All merges to main have required reviews
- [ ] All status checks pass before merging
- [ ] No direct pushes to main
- [ ] Feature branches are properly managed
- [ ] Hotfix procedures are followed

### Violation Handling

1. **Detection**: Automated alerts for violations
2. **Investigation**: Review of violation circumstances
3. **Action**: Appropriate corrective measures
4. **Documentation**: Record of violation and resolution

## 🔧 Configuration

### GitHub Settings

#### Branch Protection Rules
```yaml
main:
  protection:
    required_status_checks:
      strict: true
      contexts:
        - "Code Quality"
        - "Security Scan"
        - "Unit Tests"
        - "Integration Tests"
        - "Docker Build"
        - "Deployment Validation"
    enforce_admins: true
    required_pull_request_reviews:
      required_approving_review_count: 2
      dismiss_stale_reviews: true
      require_code_owner_reviews: true
    restrictions:
      users: []
      teams: []
      apps: []
```

#### Repository Settings
- **Allow squash merging**: ✅ Enabled
- **Allow merge commits**: ❌ Disabled
- **Allow rebase merging**: ❌ Disabled
- **Automatically delete head branches**: ✅ Enabled

### Required Files

- `.github/workflows/branch-protection.yml` - Branch protection workflow
- `.github/workflows/deploy.yml` - Deployment workflow
- `CODEOWNERS` - Code ownership file
- `CONTRIBUTING.md` - Contribution guidelines

## 📚 Documentation

### Required Documentation Updates

- [ ] Update this document for any rule changes
- [ ] Maintain list of repository owners
- [ ] Document emergency procedures
- [ ] Keep workflow examples current

### Training Requirements

- **Repository Owners**: Full training on all procedures
- **Maintainers**: Training on development workflow
- **Contributors**: Basic workflow training

---

**Last Updated**: $(date)
**Version**: 1.0
**Maintainer**: Repository Owners
**Next Review**: Monthly
