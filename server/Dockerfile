FROM node:20-slim

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install --only=production

# Copy the rest of the application code
COPY . .

# Environment variables
ENV PORT=3001
ENV FASTAPI_URL=http://energy-api:8000

EXPOSE 3001

CMD ["node", "index.js"]
