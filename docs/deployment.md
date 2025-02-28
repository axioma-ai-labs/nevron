# Deployment

This guide covers how to deploy Nevron to your own server using Docker Compose. This is the recommended method for running Nevron in a production environment.

## Server Deployment with Docker Compose

Deploying Nevron to your server is straightforward with our Docker Compose setup. This approach allows you to run the entire application stack with minimal configuration.

### Official Docker Image

Nevron is available as an official Docker image on Docker Hub:
```bash
docker pull axiomai/nevron:latest
```

You can also build the image locally if needed:
```bash
docker build -t axiomai/nevron:latest .
```

### Deployment Steps

#### 1. Create Required Volumes

First, create the necessary volume directories based on your configuration:

```bash
# Create base directories
mkdir -p volumes/nevron/logs

# For ChromaDB (if using ChromaDB as vector store)
mkdir -p volumes/nevron/chromadb

# For Qdrant (if using Qdrant as vector store)
mkdir -p volumes/qdrant/data
mkdir -p volumes/qdrant/snapshots

# For Ollama (if using local LLM)
mkdir -p volumes/ollama/models
```

> **Note:** You only need to create volumes for the services you plan to use. For example, if you're using ChromaDB, you don't need the Qdrant volumes.

#### 2. Configure Services in docker-compose.yml

Edit your `docker-compose.yml` file to enable or disable services based on your needs. You can disable a service by adding `deploy: { replicas: 0 }` to its configuration:

```yaml
# Example: Disable Qdrant if using ChromaDB
qdrant:
  <<: *service_default
  image: qdrant/qdrant:latest
  deploy:
    replicas: 0  # This disables the Qdrant service
  # ... other configuration ...

# Example: Disable Ollama if using a third-party LLM
ollama:
  <<: *service_default
  image: ollama/ollama:latest
  deploy:
    replicas: 0  # This disables the Ollama service
  # ... other configuration ...
```

#### 3. Configure Environment Variables

Create and configure your `.env` file:

```bash
cp .env.example .env
```

Edit the `.env` file to configure:

1. **Vector Store**: Choose between ChromaDB or Qdrant
   ```bash
   # For ChromaDB
   MEMORY_BACKEND_TYPE=chroma
   
   # OR for Qdrant
   MEMORY_BACKEND_TYPE=qdrant
   ```

2. **LLM Provider**: Choose between local Ollama or a third-party LLM
   ```bash
   # For local Ollama
   LLAMA_PROVIDER=ollama
   LLAMA_OLLAMA_MODEL=llama3:8b-instruct
   
   # OR for third-party LLMs (choose one)
   OPENAI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   XAI_API_KEY=your_key_here
   # etc.
   ```

For a complete list of configuration options, refer to the [Configuration](configuration.md) documentation.

#### 4. Start the Services

Launch the Nevron stack:

```bash
docker compose up -d
```

#### 5. Monitor Logs

View the logs to ensure everything is running correctly:

```bash
docker compose logs --follow
```

#### 6. Stop Services (When Needed)

To stop all services:

```bash
docker compose down
```

### Configuration Details

Our Docker Compose setup includes:

1. **Service Definitions**
   - Automatic restart policies
   - Proper logging configuration
   - Network isolation for security

2. **Volume Management**
   - Persistent storage for logs and data
   - Configurable volume base directory

3. **Networking**
   - Internal network for service communication
   - External network for API access

4. **Environment Configuration**
   - Environment file support
   - Override capability for all settings

## Production Considerations

When deploying to production, consider the following:

1. **Security**
   - Use secure storage for API keys and sensitive data
   - Consider using Docker secrets for sensitive information
   - Implement proper network security rules

2. **Performance**
   - Configure appropriate resource limits for containers
   - Monitor resource usage and adjust as needed
   - Consider using a dedicated server for high-traffic deployments

3. **Reliability**
   - Set up health checks and automatic restarts
   - Implement proper backup strategies for memory backends
   - Use a production-grade process manager

4. **Monitoring**
   - Set up proper logging and monitoring
   - Implement alerting for critical issues
   - Regularly check logs for errors or warnings

5. **Scaling**
   - For high-load scenarios, consider scaling the vector database separately
   - Use a load balancer if deploying multiple Nevron instances

For optimal production deployments, we recommend:
- Setting `ENVIRONMENT=production` in your configuration
- Regular backups of memory storage
- Using a reverse proxy (like Nginx or Traefik) for any exposed endpoints
- Implementing proper monitoring and alerting 