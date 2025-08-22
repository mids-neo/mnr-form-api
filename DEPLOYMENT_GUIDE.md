# Deployment Guide - MNR Form API

## Local Development

### Quick Start
```bash
cd /home/mids-neo/mnr-app/mnr-form-api

# Option 1: Using shell script
./start.sh

# Option 2: Using Python script
python run_server.py

# Option 3: Using Python module
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Docker Deployment

### Build and Run Locally
```bash
# Build the Docker image
docker build -t mnr-form-api .

# Run the container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="your-key" \
  -e ENV="production" \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/static:/app/static \
  mnr-form-api
```

### Docker Compose
```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.production.yml up -d
```

## AWS Deployment

### Prerequisites
- AWS CLI configured
- Docker installed
- OpenAI API key

### ECS Fargate Deployment
```bash
# Deploy to AWS ECS
./deploy-backend-ecs.sh

# The script will:
# 1. Build Docker image
# 2. Push to ECR
# 3. Update ECS service
# 4. Deploy to Fargate
```

### Environment Variables (AWS)
Set these in ECS Task Definition or Parameter Store:
- `OPENAI_API_KEY` - Your OpenAI API key
- `ENV` - Set to "production"
- `API_HOST` - "0.0.0.0"
- `API_PORT` - "8000"
- `PYTHONPATH` - "/app" (automatically set in Docker)

### Health Check
The application provides a health endpoint at `/health` for monitoring.

## File Structure on AWS

```
/app/
├── src/              # Application code
│   ├── main.py       # Entry point
│   ├── auth/         # Authentication
│   ├── pipeline/     # Processing
│   └── utils/        # Utilities
├── static/           # Static assets
│   └── templates/    # PDF templates
├── data/             # Runtime data (volumes)
│   ├── uploads/      # User uploads
│   └── outputs/      # Generated files
└── run_server.py     # Startup script
```

## Important Notes

1. **PYTHONPATH**: The Docker container sets `PYTHONPATH=/app` automatically
2. **Volumes**: Data directories are mounted as volumes for persistence
3. **Port**: Application runs on port 8000 internally
4. **Health Checks**: Built into Docker and ECS configurations
5. **Logging**: Application logs to stdout for CloudWatch integration

## Troubleshooting

### Import Errors
- The application uses `run_server.py` which handles path configuration
- Docker sets `PYTHONPATH=/app` automatically
- All imports use `src.` prefix

### File Not Found
- Ensure volumes are properly mounted
- Check that `data/` and `static/` directories exist
- Templates should be in `static/templates/`

### CORS Issues
- CORS is configured in `src/config.py`
- Add your domain to `get_cors_origins()` function
- Set `FRONTEND_URL` environment variable for custom domains

## Security

- Never commit `.env` files
- Use AWS Secrets Manager or Parameter Store for sensitive data
- Database files are in `src/auth/` and should not be in Docker image
- Use HTTPS in production (handled by ALB/CloudFront)