#!/bin/bash

# Navigate to the website directory
cd website

# Install dependencies if needed
npm install

# Build the SvelteKit app with production environment
npm run build

# Navigate back to the root directory
cd ..

# Start the FastAPI server
python server.py 