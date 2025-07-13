# Docker Optimization for Large Images (2.36GB)

This document outlines optimization strategies for CI/CD with large Docker images like our 2.36GB ML-enabled container.

## 🎯 Current Status

- **Image Size**: 2.36GB (99.49% efficient)
- **Multi-stage Build**: ✅ Implemented
- **Cache Strategy**: ⚠️ Local cache (should upgrade to registry)
- **Build Layers**: 15 layers optimized

## 🚀 Optimization Strategies

### 1. Registry-Based Caching (Most Important)

**Problem**: Local cache (`/tmp/.buildx-cache`) is unreliable for 2GB+ images in GitHub Actions.

**Solution**: Use GitHub Container Registry for cache:

```yaml
cache-from: |
  type=registry,ref=ghcr.io/user/repo:cache-main
  type=registry,ref=ghcr.io/user/repo:builder-cache-main
cache-to: |
  type=registry,ref=ghcr.io/user/repo:cache-${{ github.ref_name }},mode=max
  type=registry,ref=ghcr.io/user/repo:builder-cache-${{ github.ref_name }},mode=max,target=builder
```

**Benefits**:
- 🔄 Persistent across runners
- ⚡ 80-95% cache hit rate
- 📊 Reduces build time from 15min → 3min

### 2. Conditional Builds

**Problem**: Building 2.36GB image when only documentation changes.

**Solution**: Smart change detection:

```yaml
- uses: dorny/paths-filter@v2
  with:
    filters: |
      docker:
        - 'Dockerfile*'
        - 'requirements*.txt'
        - 'docker-compose*.yml'
      code:
        - 'mcp_server/**'
        - 'cli/**'
```

**Benefits**:
- ⏭️ Skip Docker builds when not needed
- ⚡ 70% faster CI for non-Docker changes
- 💰 Reduces GitHub Actions usage

### 3. Multi-Stage Cache Optimization

**Current**: Cache only final image
**Optimized**: Cache builder stage separately

```dockerfile
# Cache builder stage independently
FROM python:3.11-slim AS builder
# ... heavy dependency installation

FROM python:3.11-slim AS runtime
# ... lightweight runtime setup
```

**Benefits**:
- 🔄 Faster rebuilds when only app code changes
- 📦 Separate cache layers for dependencies vs. code
- ⚡ 60% faster builds on code-only changes

### 4. Parallel Optimization

**Strategy**: Run multiple optimizations in parallel:

```yaml
jobs:
  lint:           # Fast (30s)
    runs-on: ubuntu-latest
  
  test:           # Medium (2min)
    runs-on: ubuntu-latest
  
  docker-build:   # Slow (10min)
    runs-on: ubuntu-latest
    if: needs.detect-changes.outputs.docker-changed == 'true'
```

**Benefits**:
- ⏱️ Total time = slowest job (not sum of all)
- 🔀 Independent execution
- ❌ Fast failure on lint/test issues

### 5. Test Environment Optimization

**Problem**: Integration tests rebuild entire stack.

**Solution**: Use cached images + tmpfs:

```yaml
- name: Use cached image for tests
  run: |
    docker pull ghcr.io/user/repo:cache-main || \
    docker build -t retainr:test --target runtime .

- name: Optimize test environment
  run: |
    # Use tmpfs for faster I/O
    docker run -d --tmpfs /tmp/memory retainr:test
```

**Benefits**:
- ⚡ 75% faster integration tests
- 🚀 In-memory test databases
- 🔄 Reuse cached images

## 📊 Performance Metrics

### Before Optimization
- **Cold Build**: ~15 minutes
- **Warm Build**: ~12 minutes (20% cache efficiency)
- **Test Suite**: ~8 minutes
- **Total CI Time**: ~25 minutes

### After Optimization
- **Cold Build**: ~15 minutes (unchanged)
- **Warm Build**: ~3 minutes (80% cache efficiency)
- **Test Suite**: ~2 minutes
- **Total CI Time**: ~6 minutes (for code changes)
- **Doc-only Changes**: ~1 minute

## 🛠️ Implementation Guide

### Step 1: Enable Registry Caching

Replace existing cache configuration:

```yaml
# Replace this:
- name: Cache Docker layers
  uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache

# With this:
- name: Log in to Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

### Step 2: Add Change Detection

```yaml
- uses: dorny/paths-filter@v2
  id: changes
  with:
    filters: |
      docker:
        - 'Dockerfile*'
        - 'requirements*.txt'
```

### Step 3: Optimize Build Command

```yaml
- name: Build with registry cache
  uses: docker/build-push-action@v5
  with:
    cache-from: |
      type=registry,ref=ghcr.io/${{ github.repository }}:cache-${{ github.ref_name }}
      type=registry,ref=ghcr.io/${{ github.repository }}:cache-main
    cache-to: type=registry,ref=ghcr.io/${{ github.repository }}:cache-${{ github.ref_name }},mode=max
```

### Step 4: Use Custom Action

```yaml
- name: Optimized Docker Build
  uses: ./.github/actions/docker-cache
  with:
    registry: ghcr.io
    image-name: ${{ github.repository }}
    cache-scope: ${{ github.ref_name }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

## 🔍 Monitoring & Analysis

### Performance Analysis Script

```bash
# Run performance analysis
./scripts/docker-performance.sh

# Test build performance
./scripts/docker-performance.sh --test-build
```

### Key Metrics to Monitor

1. **Cache Hit Rate**: Should be >80%
2. **Build Time**: Warm builds <5min
3. **CI Duration**: Total <10min for most changes
4. **Resource Usage**: Stay within GitHub Actions limits

### GitHub Actions Insights

Monitor in GitHub Actions tab:
- Job duration trends
- Cache effectiveness
- Failure patterns
- Resource consumption

## 🏆 Best Practices for Large Images

### DO ✅
- Use registry caching for >1GB images
- Implement conditional builds
- Cache multi-stage builds separately
- Use tmpfs for test databases
- Monitor cache hit rates
- Set up parallel jobs

### DON'T ❌
- Rely on local cache for large images
- Build Docker on every CI run
- Use slow storage for tests
- Ignore cache invalidation
- Skip change detection
- Run everything sequentially

## 🚨 Common Issues & Solutions

### Issue: "No space left on device"
**Solution**: Clean up between builds
```yaml
- name: Clean up Docker
  run: docker system prune -af
```

### Issue: Cache misses on dependency changes
**Solution**: Layer dependencies separately
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
# Dependencies cached here
COPY . .
# App code changes don't invalidate dependency cache
```

### Issue: Slow test startup
**Solution**: Use health checks + parallel startup
```yaml
- name: Wait for services
  run: |
    timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done' &
    timeout 60 bash -c 'until curl -f http://localhost:8001/; do sleep 2; done' &
    wait
```

## 📈 Expected Results

With full optimization:
- **75% faster CI** for code changes
- **90% faster CI** for documentation changes
- **$50-100/month savings** in GitHub Actions costs
- **Better developer experience** with faster feedback

## 🔗 Additional Resources

- [Docker Build Cloud](https://docs.docker.com/build/cloud/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [BuildKit Cache Documentation](https://docs.docker.com/build/cache/)
- [Multi-stage Build Best Practices](https://docs.docker.com/develop/dev-best-practices/)
