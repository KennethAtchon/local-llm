#!/usr/bin/env python3
"""
Image Generation Agent using Ollama Flux Models
Generates images from text prompts using local Ollama image generation models
"""

import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests
from memory import AgentMemory

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_IMAGE_MODEL = os.getenv("OLLAMA_IMAGE_MODEL", "flux:1.1-pro")
OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR", "./generated_images")

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR

def check_ollama_connection():
    """Check if Ollama is running"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def check_model_available(model_name: str) -> bool:
    """Check if the image generation model is available"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return any(model_name in name for name in model_names)
        return False
    except Exception:
        return False

def generate_image(prompt: str, model: str = None, num_images: int = 1) -> list:
    """
    Generate image(s) from a text prompt using Ollama
    
    Args:
        prompt: Text description of the image to generate
        model: Model name (defaults to OLLAMA_IMAGE_MODEL)
        num_images: Number of images to generate (default: 1)
    
    Returns:
        List of base64-encoded image strings
    """
    if model is None:
        model = OLLAMA_IMAGE_MODEL
    
    # Ollama image generation endpoint
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    generated_images = []
    
    for i in range(num_images):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            print(f"   Generating image {i+1}/{num_images}...", end="", flush=True)
            response = requests.post(url, json=payload, timeout=600)  # 10 min timeout for image gen
            
            if response.status_code == 200:
                result = response.json()
                # Ollama flux models return image as base64 string in the response field
                # The response is a base64-encoded PNG image
                if "response" in result:
                    # Extract base64 image data
                    image_data = result["response"]
                    # Remove any prefix if present (data:image/png;base64,)
                    if "," in image_data:
                        image_data = image_data.split(",")[1]
                    generated_images.append(image_data)
                    print(" ✅")
                elif "image" in result:
                    generated_images.append(result["image"])
                    print(" ✅")
                else:
                    # Try to get raw response
                    print(f"\n   ⚠️  Response format: {list(result.keys())}")
                    # Sometimes the image is directly in the response
                    if isinstance(result, str):
                        generated_images.append(result)
                        print(" ✅")
                    else:
                        print(f"\n   ⚠️  Unexpected response format")
                        return []
            else:
                error_text = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
                print(f"\n   ❌ Error: {response.status_code} - {error_text}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"\n   ❌ Timeout: Image generation took too long (max 10 minutes)")
            return []
        except Exception as e:
            print(f"\n   ❌ Error generating image: {str(e)}")
            return []
    
    return generated_images

def save_image(base64_image: str, prompt: str, output_dir: str) -> str:
    """Save base64-encoded image to file"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(base64_image)
        
        # Create filename from prompt (sanitized)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c for c in prompt[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"{timestamp}_{safe_prompt}.png"
        filepath = os.path.join(output_dir, filename)
        
        # Save image
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return filepath
    except Exception as e:
        print(f"   ❌ Error saving image: {str(e)}")
        return None

def main():
    """Main interactive loop for image generation"""
    print("=" * 60)
    print("Image Generation Agent")
    print("=" * 60)
    print(f"Model: {OLLAMA_IMAGE_MODEL}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("\nAvailable capabilities:")
    print("  - Generate images from text prompts")
    print("  - Create multiple variations")
    print("  - Save generated images automatically")
    print("\nType 'exit' or 'quit' to stop\n")
    print("-" * 60)
    
    # Check Ollama connection
    if not check_ollama_connection():
        print(f"\n❌ Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    
    # Check if model is available
    if not check_model_available(OLLAMA_IMAGE_MODEL):
        print(f"\n⚠️  Model {OLLAMA_IMAGE_MODEL} not found")
        print(f"Download it with: ollama pull {OLLAMA_IMAGE_MODEL}")
        print("\nPopular image generation models:")
        print("  - flux:1.1-pro (high quality, slower)")
        print("  - flux:dev (good quality, faster)")
        print("  - flux:schnell (fast, lower quality)")
        print("\nWould you like to continue anyway? (y/n): ", end="")
        response = input().strip().lower()
        if response != 'y':
            sys.exit(1)
    
    # Initialize memory system
    memory = AgentMemory()
    message_count = memory.get_message_count()
    if message_count > 0:
        print(f"\n📚 Loaded {message_count} messages from memory")
    
    # Ensure output directory exists
    output_dir = ensure_output_dir()
    print(f"\n✅ Output directory: {output_dir}")
    print("\n✅ Agent ready!\n")
    
    while True:
        try:
            user_input = input("\n🎨 Prompt: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Parse for number of images
            num_images = 1
            if "x" in user_input.lower() or "generate" in user_input.lower():
                # Try to extract number (e.g., "generate 3 images of a cat")
                parts = user_input.lower().split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i > 0 and parts[i-1] in ["generate", "x", "create"]:
                        num_images = int(part)
                        # Remove the number from prompt
                        user_input = " ".join([p for j, p in enumerate(user_input.split()) if not (j == i and p.isdigit())])
                        break
            
            # Save user prompt to memory
            memory.add_message("human", f"Generate image: {user_input}")
            
            print(f"\n🖼️  Generating {num_images} image(s)...")
            
            # Generate images
            images = generate_image(user_input, num_images=num_images)
            
            if images:
                print(f"\n✅ Generated {len(images)} image(s)!")
                
                # Save images
                saved_paths = []
                for i, img in enumerate(images):
                    filepath = save_image(img, user_input, output_dir)
                    if filepath:
                        saved_paths.append(filepath)
                        print(f"   💾 Saved: {filepath}")
                
                # Save response to memory
                response_text = f"Generated {len(images)} image(s) from prompt: {user_input}"
                if saved_paths:
                    response_text += f"\nSaved to: {', '.join(saved_paths)}"
                memory.add_message("ai", response_text)
                
                print(f"\n📁 Images saved to: {output_dir}")
            else:
                print("\n❌ Failed to generate images")
                memory.add_message("ai", f"Failed to generate image from prompt: {user_input}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Try rephrasing your prompt or check the error above.")

if __name__ == "__main__":
    main()
