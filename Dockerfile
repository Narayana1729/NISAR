# Multi-stage production container for NISAR SAR Platform
FROM node:24-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --ignore-engines

# Copy application source and build assets
COPY . .
RUN npm run build

# Runtime stage
FROM node:24-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8080
ENV HOST=0.0.0.0

# Copy all application files and built bundle
COPY --from=builder /app ./

EXPOSE 8080

# Start production server
CMD ["node", "server.mjs"]
