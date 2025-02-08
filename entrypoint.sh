#!/usr/bin/bash

set -x
set -euo pipefail

# Run the main application
echo "Starting the main application..."
exec poetry run python -m src.main