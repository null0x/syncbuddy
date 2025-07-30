#!/bin/bash
set -e

echo "Checking for pipx..."

if ! command -v pipx &> /dev/null
then
    echo "pipx not found, installing pipx..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    echo "Restart your shell or run 'exec \$SHELL' to update PATH."
    exit 1
fi

echo "Building wheel for syncbuddy..."
python3 -m build

WHEEL_FILE=$(ls dist/syncbuddy-*.whl | head -n 1)

if [ -z "$WHEEL_FILE" ]; then
    echo "Error: Wheel file not found in dist/"
    exit 1
fi

echo "Uninstalling any existing syncbuddy installation from pipx..."
pipx uninstall syncbuddy || true

echo "Installing syncbuddy from wheel using pipx..."
pipx install "$WHEEL_FILE"

echo "syncbuddy installed successfully via pipx."
echo "You can now run 'syncbuddy' from your terminal."
