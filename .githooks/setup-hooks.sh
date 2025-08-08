#!/bin/bash
# Setup script for git hooks
# Run this script to install the git hooks in your local repository

echo "🔧 Setting up git hooks for Gartan Scraper Bot..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy hooks and make them executable
hooks=("pre-commit" "pre-push")

for hook in "${hooks[@]}"; do
    if [ -f ".githooks/$hook" ]; then
        cp ".githooks/$hook" ".git/hooks/$hook"
        chmod +x ".git/hooks/$hook"
        echo "✅ Installed $hook hook"
    else
        echo "❌ Hook file not found: .githooks/$hook"
        exit 1
    fi
done

# Configure git to use the hooks directory
git config core.hooksPath .githooks

echo "🎉 Git hooks setup complete!"
echo ""
echo "Hooks installed:"
echo "  - pre-commit: Runs syntax checks, tests, and validations"
echo "  - pre-push: Runs comprehensive tests and Docker build"
echo ""
echo "To bypass hooks temporarily, use:"
echo "  git commit --no-verify"
echo "  git push --no-verify"
