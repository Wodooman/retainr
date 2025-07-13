#!/bin/bash

# Script to set up branch protection rules for retainr repository
# Requires GitHub CLI (gh) to be installed and authenticated

set -e

REPO_OWNER="Wodooman"
REPO_NAME="retainr"

echo "🔒 Setting up branch protection rules for $REPO_OWNER/$REPO_NAME"

# Check if gh CLI is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed. Please install it first:"
    echo "   https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI is not authenticated. Please run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is ready"

# Required status checks
REQUIRED_CHECKS='["Code Quality (Required)","Unit Tests (Required) (3.9)","Unit Tests (Required) (3.11)","Unit Tests (Required) (3.12)","Security Check (Required)","Docker Build (Required)","PR Checks Summary"]'

echo ""
echo "📋 Required status checks:"
echo "  - Code Quality (Required)"
echo "  - Unit Tests (Required) (3.9, 3.11, 3.12)"
echo "  - Security Check (Required)"
echo "  - Docker Build (Required)"
echo "  - PR Checks Summary"

# Function to set up branch protection
setup_branch_protection() {
    local branch=$1
    echo ""
    echo "🛡️ Setting up protection for '$branch' branch..."

    # Create the protection rule
    gh api repos/$REPO_OWNER/$REPO_NAME/branches/$branch/protection \
        --method PUT \
        --field required_status_checks="{\"strict\":true,\"contexts\":$REQUIRED_CHECKS}" \
        --field enforce_admins=true \
        --field required_pull_request_reviews='{
            "required_approving_review_count":1,
            "dismiss_stale_reviews":true,
            "require_code_owner_reviews":false,
            "require_last_push_approval":false
        }' \
        --field restrictions=null \
        --field allow_force_pushes=false \
        --field allow_deletions=false \
        --field required_conversation_resolution=true

    echo "✅ Branch protection enabled for '$branch'"
}

# Set up protection for main branch
if gh api repos/$REPO_OWNER/$REPO_NAME/branches/main &> /dev/null; then
    setup_branch_protection "main"
else
    echo "⚠️ 'main' branch not found, skipping"
fi

# Set up protection for develop branch
if gh api repos/$REPO_OWNER/$REPO_NAME/branches/develop &> /dev/null; then
    setup_branch_protection "develop"
else
    echo "⚠️ 'develop' branch not found, skipping"
fi

echo ""
echo "🎉 Branch protection setup complete!"
echo ""
echo "📝 What's protected:"
echo "  ✅ Require PR reviews (1 approver)"
echo "  ✅ Require all status checks to pass"
echo "  ✅ Require branches to be up to date"
echo "  ✅ Require conversation resolution"
echo "  ✅ Dismiss stale reviews on new commits"
echo "  ✅ Restrict force pushes and deletions"
echo "  ✅ Enforce for administrators"
echo ""
echo "🔍 View protection settings:"
echo "  https://github.com/$REPO_OWNER/$REPO_NAME/settings/branches"
echo ""
echo "📖 See .github/BRANCH_PROTECTION.md for detailed documentation"
