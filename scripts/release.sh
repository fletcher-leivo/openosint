#!/bin/bash
set -e

VERSION=$1

if [ -z "$VERSION" ]; then
  echo "Usage: ./scripts/release.sh 1.0.0"
  exit 1
fi

echo "Releasing v$VERSION..."

# Update version in pyproject.toml
sed -i '' "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Update version in openosint/__init__.py
sed -i '' "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" openosint/__init__.py

# Commit version bump
git add pyproject.toml openosint/__init__.py
git commit -m "chore: bump version to v$VERSION"

# Tag and push
git tag "v$VERSION"
git push origin main
git push origin "v$VERSION"

echo "Done! GitHub Actions will now build and publish to PyPI automatically."
echo "Monitor at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//' | sed 's/.git$//')/actions"
