#!/bin/bash

echo "Setting up Ollama model for gynecology consultation..."

# Navigate to models directory
cd "$(dirname "$0")/../app/models"

# Create the custom model
ollama create gemma3-medical -f Modelfile

# Verify creation
echo ""
echo "Available models:"
ollama list

echo ""
echo "Model setup complete! You can now run: python main.py"