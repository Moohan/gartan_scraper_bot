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

echo "Setting up git hooks..."
chmod +x .githooks/pre-commit .githooks/pre-push || true

# Prefer symlinks; if filesystem blocks them (Windows with git config), fallback to copy
link_or_copy() {
    local src="$1" dst="$2"
    if ln -sf "$src" "$dst" 2>/dev/null; then
        echo "Linked $dst -> $src"
    else
        cp "$src" "$dst"
        echo "Copied $src -> $dst (symlink fallback)"
    fi
}

mkdir -p .git/hooks
link_or_copy .githooks/pre-commit .git/hooks/pre-commit
link_or_copy .githooks/pre-push .git/hooks/pre-push
echo "Git hooks installed."
