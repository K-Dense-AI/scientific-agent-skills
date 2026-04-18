#!/bin/bash
# Quick start for local development with ngrok
echo "Starting Ray-Ban Meta Assistant..."
echo "================================="

# Start server in background
uvicorn rayban_meta.main:app --port 8080 --reload &
SERVER_PID=$!

echo "Server started (PID: $SERVER_PID)"
echo "Starting ngrok tunnel..."

# Start ngrok
ngrok http 8080

# Cleanup on exit
kill $SERVER_PID 2>/dev/null
