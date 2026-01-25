#!/bin/bash
# Script to make python3 point to Python 3.12

set -e

echo "🔧 Fixing python3 to point to Python 3.12..."
echo ""
echo "Note: Python 3.8.9 at /usr/bin/python3 is the macOS system Python (not Homebrew)."
echo "We'll prioritize Homebrew's Python 3.12 by updating your PATH."
echo ""

# 1. Unlink old Homebrew Python versions (if any)
echo "Step 1: Unlinking old Homebrew Python versions..."
brew unlink python@3.9 2>/dev/null || echo "  python@3.9 already unlinked or not found"

# 2. Link Python 3.12
echo "Step 2: Linking Python 3.12..."
brew link --overwrite --force python@3.12

# 3. Check if PATH update is needed
# The system Python at /usr/bin/python3 (3.8.9) is being found first
# We need to ensure /usr/local/bin comes before /usr/bin in PATH
if ! grep -q 'export PATH="/usr/local/bin:$PATH"' ~/.zshrc 2>/dev/null; then
    echo "Step 3: Updating ~/.zshrc to prioritize Homebrew Python over system Python..."
    echo '' >> ~/.zshrc
    echo '# Prioritize Homebrew Python (3.12) over system Python (3.8.9)' >> ~/.zshrc
    echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
    echo "  ✅ Added PATH update to ~/.zshrc"
else
    echo "Step 3: PATH already configured in ~/.zshrc"
fi

# 4. Verify current shell
echo ""
echo "Step 4: Verifying in current shell..."
export PATH="/usr/local/bin:$PATH"

# 5. Check results
echo ""
echo "📋 Results:"
echo "  which python3: $(which python3)"
echo "  python3 --version: $(python3 --version)"
echo "  python3.12 --version: $(python3.12 --version)"

echo ""
echo "✅ Done! Run 'source ~/.zshrc' or open a new terminal to apply changes."
echo ""
echo "If python3 still shows 3.8.9, run: source ~/.zshrc"
