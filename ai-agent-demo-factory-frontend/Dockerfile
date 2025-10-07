# Use a Node.js official image as the base for building and serving the React app
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json from the correct location
# Note: The COPY path should be relative to the build context
COPY package*.json ./

# Install project dependencies
RUN npm ci

# Copy the rest of your frontend application files
COPY . /app

# Expose the port your React development server typically runs on
EXPOSE 3000

# Command to start the React development server
# Use npm start for Create React App, or npm run dev for Vite
CMD ["npm", "run" , "dev"]