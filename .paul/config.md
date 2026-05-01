# Project Config

**Project:** Review Radar
**Created:** 2026-05-02

## Project Settings

```yaml
project:
  name: review-radar
  version: 0.0.0
```

## Integrations

### SonarQube

```yaml
sonarqube:
  enabled: true
  project_key: review-radar
```

**Setup note:** Connect via GitHub after creating the remote repo.
1. Push to GitHub
2. Go to sonarcloud.io → Create project → Import from GitHub → select `review-radar`
3. SonarQube will auto-detect the project key

### Enterprise Plan Audit

```yaml
enterprise_plan_audit:
  enabled: true
```

**What this does:** Before each APPLY, `/paul:audit` runs an architectural review of the PLAN — checks for scope creep, missing error handling, security gaps, and integration risks. Surfaces issues before code is written.

## Preferences

```yaml
preferences:
  auto_commit: false
  verbose_output: false
```

---
*Config created: 2026-05-02*
