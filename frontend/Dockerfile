FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

# Copy source
COPY . .

# Expose Vite port
EXPOSE 3000

# Start development server
CMD ["yarn", "dev", "--host"]
