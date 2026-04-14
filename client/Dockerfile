FROM node:20-slim

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the application code
COPY . .

# Expose Vite's default dev port
EXPOSE 5173

# Run Vite with --host to allow external access (from outside the container)
CMD ["npm", "run", "dev", "--", "--host"]
