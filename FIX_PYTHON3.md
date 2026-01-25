# Fix python3 to Point to Python 3.12

The issue is that `/usr/bin/python3` (system Python 3.8.9) is taking precedence over Homebrew's Python 3.12.

**Important:** Python 3.8.9 at `/usr/bin/python3` is the macOS system Python (not managed by Homebrew), so we can't unlink it. Instead, we need to prioritize Homebrew's Python by updating your PATH.

## Solution: Update Your Shell Configuration

Run these commands in your terminal:

```bash
# 1. Unlink old Homebrew Python versions (if any)
brew unlink python@3.9 2>/dev/null || true

# 2. Link Python 3.12
brew link --overwrite --force python@3.12

# 3. Update your ~/.zshrc to prioritize Homebrew's Python
cat >> ~/.zshrc << 'EOF'

# Prioritize Homebrew Python over system Python
export PATH="/usr/local/bin:$PATH"
EOF

# 4. Reload your shell configuration
source ~/.zshrc

# 5. Verify it works
which python3
python3 --version  # Should show Python 3.12.12
```

## Alternative: Create an Alias (Quick Fix)

If the above doesn't work, you can add an alias to your `~/.zshrc`:

```bash
echo 'alias python3=python3.12' >> ~/.zshrc
echo 'alias pip3=pip3.12' >> ~/.zshrc
source ~/.zshrc
```

## Verify

After running the commands, verify:
```bash
which python3    # Should show /usr/local/bin/python3
python3 --version # Should show Python 3.12.12
```

## If It Still Doesn't Work

Check your PATH order:
```bash
echo $PATH | tr ':' '\n' | grep -E "(usr/local|usr/bin)"
```

`/usr/local/bin` should come **before** `/usr/bin` in your PATH.
