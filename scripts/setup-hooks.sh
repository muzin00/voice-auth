#!/usr/bin/env bash
# Setup git hooks using uvx (no virtualenv required)
# This script works in both main repo and git worktrees

set -e

# Find the git directory (handles worktrees)
GIT_DIR=$(git rev-parse --git-dir)
HOOKS_DIR="$GIT_DIR/hooks"

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/usr/bin/env bash
# Pre-commit hook using uvx (virtualenv-independent)

# Find the repository root
REPO_ROOT=$(git rev-parse --show-toplevel)

# Change to repo root and run pre-commit via uvx
cd "$REPO_ROOT"
exec uvx pre-commit run
EOF

chmod +x "$HOOKS_DIR/pre-commit"

echo "✓ Pre-commit hook installed to $HOOKS_DIR/pre-commit"
