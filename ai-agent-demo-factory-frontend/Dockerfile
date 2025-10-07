# Frontend Dockerfile for Next.js - Development Mode
FROM node:20-alpine

WORKDIR /app

# Install build dependencies for native modules
RUN apk add --no-cache libc6-compat python3 make g++

# Copy only package.json first
COPY package.json ./

# Generate fresh lockfile for Alpine Linux platform
RUN npm install

# Copy application source
COPY . .

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Run in development mode
CMD ["npm", "run", "dev"]