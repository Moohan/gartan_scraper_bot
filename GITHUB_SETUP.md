# GitHub Repository Configuration

## Required Secrets

To enable automated Docker Hub publishing, add these secrets to your GitHub repository:

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add the following repository secrets:

| Secret Name | Value | Description |
|-------------|--------|-------------|
| `DOCKER_USERNAME` | `moohan` | Your Docker Hub username |
| `DOCKER_PASSWORD` | `[your-docker-hub-token]` | Docker Hub access token (not password) |

## Creating Docker Hub Access Token

1. Go to [Docker Hub](https://hub.docker.com/)
2. Sign in to your account
3. Go to Account Settings → Security
4. Click "New Access Token"
5. Name: `github-actions-gartan-scraper`
6. Permissions: `Read, Write, Delete`
7. Copy the generated token and use it as `DOCKER_PASSWORD`

## Workflow Triggers

The CI/CD pipeline will automatically:

- **On every push to main**: Build and publish `moohan/gartan_scraper_bot:latest`
- **On every commit**: Build and publish `moohan/gartan_scraper_bot:sha-abcd123`
- **On version tags**: Create releases and publish `moohan/gartan_scraper_bot:v1.x.x`

## Deployment Commands

Once the image is published, you can deploy anywhere with:

```bash
# Simple deployment
docker run -d \
  -p 5000:5000 \
  -e GARTAN_USERNAME=your_username \
  -e GARTAN_PASSWORD=your_password \
  --name gartan-scrape \
  moohan/gartan_scraper_bot:latest

# Or with docker-compose
docker-compose up -d
```

## Repository Setup Checklist

- [x] Git hooks configured (pre-commit, pre-push)
- [x] GitHub Actions workflows created (ci.yml, release.yml, security.yml)
- [x] Docker Hub publishing configured
- [x] docker-compose.yml updated for published image
- [ ] GitHub secrets configured (DOCKER_USERNAME, DOCKER_PASSWORD)
- [ ] First push to trigger initial image build

After configuring the secrets, push your changes to GitHub to trigger the first automated build and publish!
