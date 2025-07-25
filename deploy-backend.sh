#!/bin/bash

# FastAPI Backend Deployment Script

set -e

echo "🚀 Starting FastAPI Backend Deployment..."

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found!"
    echo "Please create .env.production with your production settings."
    exit 1
fi

# Copy production env file
cp .env.production .env

echo "📦 Building backend Docker image..."
docker compose -f docker-compose.backend.yml build backend

echo "🔄 Stopping existing containers..."
docker compose -f docker-compose.backend.yml down

echo "🚀 Starting backend service..."
docker compose -f docker-compose.backend.yml up -d

echo "⏳ Waiting for backend to be healthy..."
sleep 30

# Check if backend is healthy
if docker compose -f docker-compose.backend.yml ps | grep -q "healthy"; then
    echo "✅ Backend deployment successful!"
    echo "🌐 Backend API available at: http://$(hostname -I | awk '{print $1}'):9102"
    echo "📚 API Documentation: http://$(hostname -I | awk '{print $1}'):9102/docs"
else
    echo "❌ Backend deployment failed. Checking logs..."
    docker compose -f docker-compose.backend.yml logs backend
    exit 1
fi

echo "📋 Deployment Summary:"
echo "- Backend API: http://$(hostname -I | awk '{print $1}'):9102"
echo "- API Docs: http://$(hostname -I | awk '{print $1}'):9102/docs"
echo "- Health Check: http://$(hostname -I | awk '{print $1}'):9102/api/v1/utils/health-check/"

echo "🔧 Useful commands:"
echo "- View logs: docker compose -f docker-compose.backend.yml logs -f backend"
echo "- Restart: docker compose -f docker-compose.backend.yml restart backend"
echo "- Stop: docker compose -f docker-compose.backend.yml down"