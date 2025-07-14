#!/bin/bash

# Docker Performance Analysis Script
# Analyzes build performance and cache efficiency for large images

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🐳 Docker Performance Analysis for Retainr"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Analyze current Docker setup
analyze_dockerfile() {
    echo ""
    print_status $BLUE "📋 Dockerfile Analysis"
    echo "----------------------"

    if [ -f "$PROJECT_ROOT/Dockerfile" ]; then
        local dockerfile="$PROJECT_ROOT/Dockerfile"

        # Count layers
        local layers=$(grep -c "^FROM\|^RUN\|^COPY\|^ADD" "$dockerfile" || echo "0")
        echo "Total layers: $layers"

        # Check for multi-stage
        local stages=$(grep -c "^FROM.*AS" "$dockerfile" || echo "0")
        if [ "$stages" -gt 0 ]; then
            print_status $GREEN "✅ Multi-stage build detected ($stages stages)"
        else
            print_status $YELLOW "⚠️ No multi-stage build detected"
        fi

        # Check for cache optimization
        if grep -q "cache-from\|buildx\|BUILDKIT_INLINE_CACHE" "$dockerfile" || \
           find "$PROJECT_ROOT/.github" -name "*.yml" -exec grep -l "cache-from\|buildx" {} \; | grep -q .; then
            print_status $GREEN "✅ Cache optimization detected"
        else
            print_status $YELLOW "⚠️ No cache optimization detected"
        fi

        # Check .dockerignore
        if [ -f "$PROJECT_ROOT/.dockerignore" ]; then
            local ignored_items=$(wc -l < "$PROJECT_ROOT/.dockerignore")
            print_status $GREEN "✅ .dockerignore exists ($ignored_items items)"
        else
            print_status $RED "❌ .dockerignore missing"
        fi
    else
        print_status $RED "❌ Dockerfile not found"
    fi
}

# Analyze image size and layers
analyze_image_size() {
    echo ""
    print_status $BLUE "📊 Image Size Analysis"
    echo "----------------------"

    local images=$(docker images | grep retainr || true)
    if [ -z "$images" ]; then
        print_status $YELLOW "⚠️ No retainr images found locally"
        return
    fi

    echo "Local retainr images:"
    docker images retainr --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

    # Analyze layers if dive is available
    if command -v dive >/dev/null 2>&1; then
        echo ""
        print_status $BLUE "🔍 Layer Analysis (using dive)"
        echo "------------------------------"

        local latest_image=$(docker images retainr --format "{{.Repository}}:{{.Tag}}" | head -1)
        if [ -n "$latest_image" ]; then
            echo "Analyzing $latest_image..."
            dive "$latest_image" --ci --lowestEfficiency=95
        fi
    else
        print_status $YELLOW "⚠️ Install 'dive' for detailed layer analysis: https://github.com/wagoodman/dive"
    fi
}

# Test build performance
test_build_performance() {
    echo ""
    print_status $BLUE "🚀 Build Performance Test"
    echo "-------------------------"

    local dockerfile="$PROJECT_ROOT/Dockerfile"
    if [ ! -f "$dockerfile" ]; then
        print_status $RED "❌ Dockerfile not found"
        return
    fi

    echo "Testing build performance..."

    # Clean build (no cache)
    echo ""
    print_status $YELLOW "🧹 Clean build (no cache):"
    local start_time=$(date +%s)

    if docker build -t retainr:perf-test --no-cache "$PROJECT_ROOT" >/dev/null 2>&1; then
        local end_time=$(date +%s)
        local clean_duration=$((end_time - start_time))
        print_status $GREEN "✅ Clean build completed in ${clean_duration}s"
    else
        print_status $RED "❌ Clean build failed"
        return
    fi

    # Cached build (no changes)
    echo ""
    print_status $YELLOW "⚡ Cached build (no changes):"
    start_time=$(date +%s)

    if docker build -t retainr:perf-test-cached "$PROJECT_ROOT" >/dev/null 2>&1; then
        end_time=$(date +%s)
        local cached_duration=$((end_time - start_time))
        print_status $GREEN "✅ Cached build completed in ${cached_duration}s"

        # Calculate cache efficiency
        local efficiency=$((100 - (cached_duration * 100 / clean_duration)))
        if [ $efficiency -gt 80 ]; then
            print_status $GREEN "🎯 Cache efficiency: ${efficiency}% (Excellent)"
        elif [ $efficiency -gt 60 ]; then
            print_status $YELLOW "🎯 Cache efficiency: ${efficiency}% (Good)"
        else
            print_status $RED "🎯 Cache efficiency: ${efficiency}% (Poor)"
        fi
    else
        print_status $RED "❌ Cached build failed"
    fi

    # Clean up test images
    docker rmi retainr:perf-test retainr:perf-test-cached >/dev/null 2>&1 || true
}

# Analyze CI cache strategy
analyze_ci_cache() {
    echo ""
    print_status $BLUE "🔧 CI Cache Strategy Analysis"
    echo "-----------------------------"

    local ci_files=$(find "$PROJECT_ROOT/.github/workflows" -name "*.yml" 2>/dev/null || true)
    if [ -z "$ci_files" ]; then
        print_status $YELLOW "⚠️ No GitHub Actions workflows found"
        return
    fi

    for file in $ci_files; do
        echo "Analyzing $(basename "$file"):"

        # Check for Docker cache strategies
        if grep -q "cache-from.*registry" "$file"; then
            print_status $GREEN "  ✅ Registry cache detected"
        elif grep -q "cache-from" "$file"; then
            print_status $YELLOW "  ⚠️ Local cache detected (consider registry cache)"
        else
            print_status $RED "  ❌ No cache strategy detected"
        fi

        # Check for buildx
        if grep -q "docker/setup-buildx-action" "$file"; then
            print_status $GREEN "  ✅ Docker Buildx enabled"
        else
            print_status $YELLOW "  ⚠️ Docker Buildx not detected"
        fi

        # Check for multi-platform builds
        if grep -q "platforms:" "$file"; then
            print_status $GREEN "  ✅ Multi-platform build detected"
        fi

        # Check for conditional builds
        if grep -q "paths-filter\|detect-changes" "$file"; then
            print_status $GREEN "  ✅ Conditional builds detected"
        else
            print_status $YELLOW "  ⚠️ Consider conditional builds for efficiency"
        fi
    done
}

# Provide optimization recommendations
provide_recommendations() {
    echo ""
    print_status $BLUE "💡 Optimization Recommendations"
    echo "==============================="

    echo ""
    print_status $GREEN "For Large Images (2GB+):"
    echo "• Use registry cache instead of local cache"
    echo "• Implement multi-stage builds"
    echo "• Use conditional builds (skip when no Docker changes)"
    echo "• Cache builder stage separately"
    echo "• Use tmpfs for test databases"
    echo "• Pre-pull base images in parallel"
    echo "• Consider BuildKit inline cache"

    echo ""
    print_status $GREEN "CI/CD Optimizations:"
    echo "• Use GitHub Container Registry for cache"
    echo "• Implement smart cache invalidation"
    echo "• Run Docker builds conditionally"
    echo "• Use parallel jobs where possible"
    echo "• Monitor cache hit rates"

    echo ""
    print_status $GREEN "Image Size Optimizations:"
    echo "• Multi-stage builds to reduce final size"
    echo "• .dockerignore to exclude unnecessary files"
    echo "• Use slim base images"
    echo "• Remove build dependencies in final stage"
    echo "• Use compression for registry pushes"

    echo ""
    print_status $BLUE "🔗 Useful Tools:"
    echo "• dive: https://github.com/wagoodman/dive (image analysis)"
    echo "• docker-slim: https://github.com/docker-slim/docker-slim (optimization)"
    echo "• hadolint: https://github.com/hadolint/hadolint (Dockerfile linting)"
}

# Main execution
main() {
    echo "Starting Docker performance analysis..."

    analyze_dockerfile
    analyze_image_size
    analyze_ci_cache

    # Only run performance test if requested
    if [ "${1:-}" = "--test-build" ]; then
        test_build_performance
    else
        echo ""
        print_status $YELLOW "💡 Run with --test-build to test actual build performance"
    fi

    provide_recommendations

    echo ""
    print_status $GREEN "✅ Analysis complete!"
}

# Run main function
main "$@"
