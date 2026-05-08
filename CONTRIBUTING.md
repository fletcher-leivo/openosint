# Contributing to OpenOSINT

## Release Process

Releases are automated via GitHub Actions.

### First-time PyPI Setup (maintainer only)

1. Go to https://pypi.org/manage/account/publishing/
2. Add a new trusted publisher:
   - PyPI project name: `openosint`
   - Owner: your GitHub username
   - Repository: `OpenOSINT`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. Go to GitHub repo → Settings → Environments → New environment → name it `pypi`

### Cutting a Release

```bash
./scripts/release.sh 1.1.0
```

That's it. The workflow will:
1. Run tests on Python 3.10, 3.11, 3.12
2. Build the package
3. Publish to PyPI
4. Create a GitHub Release with auto-generated release notes
