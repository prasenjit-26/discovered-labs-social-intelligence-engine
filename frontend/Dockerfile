FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source
COPY . .

# Build not needed for dev, but good for prod
# RUN npm run build

# Expose Vite port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host"]
