#!/bin/bash

# Lint script for retainr - runs the same checks as CI
set -e

echo "🔍 Running code quality checks..."

# Activate virtual environment if it exists
if [ -d "test-env" ]; then
    source test-env/bin/activate
    echo "✅ Activated test environment"
fi

echo ""
echo "1️⃣ Checking code formatting with Black..."
black --check --diff .

echo ""
echo "2️⃣ Linting with Ruff..."
ruff check .

echo ""
echo "3️⃣ Type checking with MyPy..."
mypy mcp_server cli --ignore-missing-imports || echo "⚠️ MyPy found type issues (not blocking)"

echo ""
echo "✅ All checks completed!"
echo ""
echo "💡 To auto-fix issues:"
echo "   black .          # Format code"
echo "   ruff check --fix # Fix linting issues"
echo "   pre-commit run --all-files  # Run all pre-commit hooks"
