#!/bin/bash
# Setup script for glb-model-rotate UV environment

set -e

echo "Setting up glb-model-rotate Python environment with UV..."

# Check if UV is installed
if ! command -v uv &> /dev/null
then
    echo "UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "Please restart your shell or run: source $HOME/.cargo/env"
    exit 1
fi

echo "UV version: $(uv --version)"

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install trimesh pymeshlab numpy

echo ""
echo "Setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To install development dependencies, run:"
echo "  uv pip install pytest black ruff"
echo ""
echo "Python scripts are ready to use!"
echo ""
