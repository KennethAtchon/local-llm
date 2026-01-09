#!/usr/bin/env python3
"""
Image Generation Agent GUI - Gradio Interface
Generates images from text prompts using Ollama flux models
"""

import os
import sys
import base64
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr
import requests
from memory import AgentMemory
from PIL import Image
import io

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_IMAGE_MODEL = os.getenv("OLLAMA_IMAGE_MODEL", "flux:1.1-pro")
OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR", "./generated_images")

# Global memory
memory = None

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

def generate_image(prompt: str, model: str = None) -> tuple:
    """
    Generate image from a text prompt using Ollama
    
    Returns:
        Tuple of (image_data, error_message)
        image_data is base64 string or None if error
    """
    if model is None:
        model = OLLAMA_IMAGE_MODEL
    
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=600)  # 10 min timeout
        
        if response.status_code == 200:
            result = response.json()
            # Extract base64 image data
            if "response" in result:
                image_data = result["response"]
                # Remove prefix if present
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                return image_data, None
            elif "image" in result:
                return result["image"], None
            else:
                return None, f"Unexpected response format: {list(result.keys())}"
        else:
            error_text = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
            return None, f"Error {response.status_code}: {error_text}"
            
    except requests.exceptions.Timeout:
        return None, "Timeout: Image generation took too long (max 10 minutes)"
    except Exception as e:
        return None, f"Error: {str(e)}"

def base64_to_image(base64_str: str):
    """Convert base64 string to PIL Image"""
    try:
        # Remove prefix if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        return None

def save_image(base64_image: str, prompt: str, output_dir: str) -> str:
    """Save base64-encoded image to file"""
    try:
        image_data = base64.b64decode(base64_image)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c for c in prompt[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"{timestamp}_{safe_prompt}.png"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return filepath
    except Exception as e:
        return None

def generate_and_display(prompt: str, num_images: int, history):
    """Generate image and display in chat"""
    global memory
    
    if not prompt:
        return history, None, "Please enter a prompt"
    
    if memory is None:
        memory = AgentMemory()
    
    # Save prompt to memory
    memory.add_message("human", f"Generate image: {prompt}")
    
    generated_images = []
    errors = []
    
    for i in range(num_images):
        image_data, error = generate_image(prompt, OLLAMA_IMAGE_MODEL)
        
        if image_data:
            # Convert to PIL Image for display
            img = base64_to_image(image_data)
            if img:
                generated_images.append(img)
                # Save image
                output_dir = ensure_output_dir()
                filepath = save_image(image_data, f"{prompt}_{i+1}", output_dir)
            else:
                errors.append(f"Failed to decode image {i+1}")
        else:
            errors.append(f"Image {i+1}: {error}")
    
    # Update history
    if history is None:
        history = []
    
    if generated_images:
        # Display first image (Gradio can show one at a time)
        display_image = generated_images[0]
        response_text = f"Generated {len(generated_images)} image(s) from: '{prompt}'"
        if errors:
            response_text += f"\n⚠️ Errors: {'; '.join(errors)}"
        
        history.append([prompt, response_text])
        memory.add_message("ai", response_text)
        
        return history, display_image, f"✅ Generated {len(generated_images)} image(s)!"
    else:
        error_msg = "; ".join(errors) if errors else "Failed to generate images"
        history.append([prompt, f"❌ {error_msg}"])
        memory.add_message("ai", f"Failed: {error_msg}")
        return history, None, f"❌ {error_msg}"

def initialize_agent():
    """Initialize and return status"""
    global memory
    
    try:
        memory = AgentMemory()
        message_count = memory.get_message_count()
        
        # Check Ollama
        if not check_ollama_connection():
            return "❌ Cannot connect to Ollama. Make sure it's running: ollama serve"
        
        # Check model
        if not check_model_available(OLLAMA_IMAGE_MODEL):
            return f"⚠️ Model {OLLAMA_IMAGE_MODEL} not found. Download with: ollama pull {OLLAMA_IMAGE_MODEL}"
        
        # Ensure output directory
        ensure_output_dir()
        
        status = f"✅ Agent ready! Model: {OLLAMA_IMAGE_MODEL}"
        if message_count > 0:
            status += f"\n📚 Loaded {message_count} messages from memory"
        
        return status
    except Exception as e:
        return f"❌ Error: {str(e)}"

def main():
    """Main function to launch the Gradio interface"""
    
    status = initialize_agent()
    
    with gr.Blocks(title="Image Generation Agent", theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"""
        # 🎨 Image Generation Agent
        
        **Model:** {OLLAMA_IMAGE_MODEL}  
        **Ollama URL:** {OLLAMA_BASE_URL}
        
        {status}
        
        ### Generate images from text prompts using AI!
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                prompt_input = gr.Textbox(
                    label="Image Prompt",
                    placeholder="Describe the image you want to generate...",
                    lines=3
                )
                num_images = gr.Slider(
                    label="Number of Images",
                    minimum=1,
                    maximum=4,
                    value=1,
                    step=1
                )
                generate_btn = gr.Button("Generate Image", variant="primary", scale=1)
                clear_btn = gr.Button("Clear", scale=1)
                refresh_btn = gr.Button("Refresh Agent", scale=1)
            
            with gr.Column(scale=1):
                image_output = gr.Image(
                    label="Generated Image",
                    height=500,
                    type="pil"
                )
                status_text = gr.Textbox(
                    label="Status",
                    value="Ready to generate images",
                    interactive=False
                )
        
        chatbot = gr.Chatbot(
            label="Generation History",
            height=300,
            show_copy_button=True
        )
        
        def generate(prompt, num, history):
            new_history, image, status_msg = generate_and_display(prompt, int(num), history)
            return new_history, image, status_msg, ""
        
        def clear_all():
            return None, None, "Cleared", ""
        
        def refresh():
            new_status = initialize_agent()
            return new_status
        
        generate_btn.click(
            generate,
            [prompt_input, num_images, chatbot],
            [chatbot, image_output, status_text, prompt_input]
        )
        clear_btn.click(clear_all, None, [chatbot, image_output, status_text, prompt_input])
        refresh_btn.click(refresh, None, status_text)
        
        gr.Markdown("""
        ### Tips:
        - Be descriptive in your prompts for better results
        - Try: "a cat wearing a hat", "futuristic city at sunset", "watercolor painting of mountains"
        - Popular models: flux:1.1-pro (quality), flux:dev (balanced), flux:schnell (fast)
        - Generated images are saved to: `generated_images/` directory
        """)
    
    demo.launch(
        server_name="127.0.0.1",
        server_port=7862,  # Different port
        share=False,
        show_error=True
    )

if __name__ == "__main__":
    main()
