#!/bin/bash
echo "--- Swarm Diagnostic ---"
echo "Checking GPU 0 (Port 11434)..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags
echo -e "\nChecking GPU 1 (Port 11435)..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:11435/api/tags
echo -e "\n--- Process Status ---"
ps aux | grep ollama
echo "------------------------"
