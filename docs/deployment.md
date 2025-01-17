# Deployment

This guide covers deployment option for Nevron using Docker.

## Docker Deployment

### Official Docker Image

Nevron is available as an official Docker image on Docker Hub:
```bash
docker pull axiomai/nevron:latest
```

Also you can build the image locally:

```bash
docker build -t axiomai/nevron:latest .
```

### Running with Docker

Basic run command:
```bash
# create directories for volumes
mkdir -p volumes/.chromadb

# run the agent
docker run -d \
  --name nevron \
  -e .env \
  -v $(pwd)/volumes/.chromadb:/app/.chromadb \
  axiomai/nevron:latest
```

### Configuration

#### Volume Mounts
- `.chromadb`: Persistent storage for ChromaDB (when using ChromaDB backend)
- `qdrant_storage`: Persistent storage for Qdrant (when using Qdrant backend)

#### Environment Variables

You'll need to set the `OPENAI_API_KEY` environment variable to be able to use the agent.

For a complete list of available environment variables, see the [Environment Variables](development/environment.md) documentation.

### Docker Compose

For production deployments, we provide a `docker-compose.yml`:

```yaml
# See the full file in the repository
services:
  nevron:
    image: axiomai/nevron:latest
    # ... configuration ...

  qdrant:
    image: qdrant/qdrant:latest
    # ... configuration ...
```

Key features of our Docker Compose setup:

1. **Service Definitions**
   - Reusable service defaults
   - Automatic restart policies
   - Proper logging configuration
   - Network isolation

2. **Volume Management**
   - Persistent storage for logs
   - Configurable volume base directory
   - Separate volumes for different components

3. **Networking**
   - Internal network for service communication
   - External network for API access
   - Bridge network driver for security

4. **Environment Configuration**
   - Environment file support
   - Override capability for all settings
   - Service-specific environment variables

To use Docker Compose:

```bash
# Create required directories
mkdir -p volumes/{nevron,qdrant}/{logs,data,snapshots}

# Add your .env file
cp .env.example .env

# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

Important:
- Make sure to set the correct environment variables in the `.env` file.
- Make sure to set the correct volume mounts in the `docker-compose.yml` file.

## Production Considerations

When deploying to production, consider the following:

1. Use a production-grade process manager (e.g., supervisord, systemd)
2. Set up proper logging and monitoring
3. Use secure storage for API keys and sensitive data
4. Configure appropriate resource limits
5. Set up health checks and automatic restarts
6. Use a reverse proxy for any exposed endpoints
7. Implement proper backup strategies for memory backends

For production deployments, we recommend:
- Using the Docker Compose deployment method
- Setting `ENVIRONMENT=production` in your configuration
- Using a dedicated memory backend instance
- Implementing proper monitoring and alerting
- Regular backups of memory storage 