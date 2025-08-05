# Stage 0, "build-stage", based on Node.js, to build and compile the frontend
FROM node:20 AS build-stage

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app

# Copy dependency definition files from the frontend directory to leverage Docker cache
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install dependencies using the lockfile
RUN pnpm install --frozen-lockfile

# Copy the rest of the application source code from the frontend directory
COPY frontend/. .

# Declare the build-time argument for the API URL
ARG VITE_API_URL

# Build the frontend
RUN pnpm run build


# Stage 1, "production-stage", based on Nginx, to serve the compiled app
FROM nginx:1

# Copy the built static files from the "build-stage"
COPY --from=build-stage /app/dist/ /usr/share/nginx/html

# Copy the custom Nginx configuration from the frontend directory
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/nginx-backend-not-found.conf /etc/nginx/extra-conf.d/backend-not-found.conf