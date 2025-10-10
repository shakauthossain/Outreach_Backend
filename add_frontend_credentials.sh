#!/bin/bash

# Add frontend login credentials to .env file
echo "" >> .env
echo "# Frontend Authentication for Screenshot Capture" >> .env
echo "FRONTEND_LOGIN_EMAIL=your-email@example.com" >> .env
echo "FRONTEND_LOGIN_PASSWORD=your-password" >> .env

echo "✅ Added frontend credentials template to .env file"
echo "⚠️  Please edit .env and replace with your actual credentials"
