# Upgrading Python on macOS

## ✅ Python 3.12 is Already Installed!

You have Python 3.12.12 installed. Use it with `python3.12` command.

You currently have Python 3.9.10 installed via Homebrew. To use the latest edgartools (5.12.0+), you need Python 3.10 or higher.

## Option 1: Upgrade Python using Homebrew (Recommended)

### Step 1: Install Python 3.12 (latest stable)
```bash
brew install python@3.12
```

### Step 2: Verify the installation
```bash
python3.12 --version
# Should show: Python 3.12.x
```

### Step 3: Update your PATH (choose one method)

**Method A: Update your shell profile (permanent)**
Add to `~/.zshrc` (since you're using zsh):
```bash
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
echo 'alias python3=python3.12' >> ~/.zshrc
echo 'alias pip3=pip3.12' >> ~/.zshrc
source ~/.zshrc
```

**Method B: Use python3.12 directly**
Just use `python3.12` and `pip3.12` commands instead of `python3` and `pip3`.

### Step 4: Reinstall Python dependencies
```bash
cd apps/api
pip3.12 install --upgrade -r requirements.txt
```

## Option 2: Use pyenv (Better for managing multiple Python versions)

### Step 1: Install pyenv
```bash
brew install pyenv
```

### Step 2: Add pyenv to your shell
```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Install Python 3.12
```bash
pyenv install 3.12.7
```

### Step 4: Set it as local version for this project
```bash
cd /Users/markphillips/storcky/apps/api
pyenv local 3.12.7
```

### Step 5: Verify and reinstall dependencies
```bash
python --version  # Should show 3.12.7
pip install --upgrade -r requirements.txt
```

## ✅ Quick Setup (Recommended - Use Python 3.12 for this project)

Since Python 3.12 is already installed, just run:

```bash
cd apps/api
./setup.sh
```

Or manually:
```bash
cd apps/api
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Then always activate the virtual environment before running:
```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

## Option 3: Make Python 3.12 the System Default

If you want `python3` to point to 3.12 system-wide:

```bash
brew unlink python@3.9
brew link python@3.12
python3 --version  # Should now show 3.12.x
```

**Warning:** This will change the system default Python version and may affect other projects.

## After Upgrading

Once you have Python 3.10+, update `requirements.txt`:
```txt
edgartools>=5.12.0
```

Then reinstall:
```bash
pip install --upgrade -r requirements.txt
```

## Verify Your Setup

After upgrading, verify everything works:
```bash
python3 --version  # Should show 3.10+
python3 -c "import edgar; print('EdgarTools imported successfully')"
```

## Troubleshooting

If you encounter issues:
1. Make sure you're using the correct Python version: `which python3`
2. Check if Homebrew Python is in your PATH: `echo $PATH`
3. For pyenv users: `pyenv versions` to see installed versions
4. For virtual environments: Make sure you activate it: `source venv/bin/activate`
