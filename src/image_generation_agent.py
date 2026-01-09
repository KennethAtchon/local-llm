#!/usr/bin/env python3
"""
Image Generation Agent using Stable Diffusion
Generates images from text prompts using local Stable Diffusion models
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from memory import AgentMemory
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
STABLE_DIFFUSION_MODEL = os.getenv("STABLE_DIFFUSION_MODEL", "runwayml/stable-diffusion-v1-5")
OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR", "./generated_images")
DEVICE = os.getenv("DEVICE", "auto")  # auto, cuda, cpu
NUM_INFERENCE_STEPS = int(os.getenv("NUM_INFERENCE_STEPS", "25"))
GUIDANCE_SCALE = float(os.getenv("GUIDANCE_SCALE", "7.5"))

# Global pipeline
pipeline = None

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR

def get_device():
    """Determine the best device to use"""
    if DEVICE != "auto":
        return DEVICE
    
    # Check for CUDA (NVIDIA) or ROCm (AMD)
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "Unknown"
        print(f"   Detected GPU: {device_name}")
        return "cuda"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon
    else:
        return "cpu"

def load_pipeline():
    """Load the Stable Diffusion pipeline"""
    global pipeline
    
    if pipeline is not None:
        return pipeline
    
    device = get_device()
    print(f"🔄 Loading Stable Diffusion model: {STABLE_DIFFUSION_MODEL}")
    print(f"   Device: {device}")
    
    try:
        # Load pipeline
        pipeline = StableDiffusionPipeline.from_pretrained(
            STABLE_DIFFUSION_MODEL,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            safety_checker=None,  # Disable safety checker for faster generation
            requires_safety_checker=False
        )
        
        # Move to device
        pipeline = pipeline.to(device)
        
        # Use faster scheduler for better speed/quality balance
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config)
        
        # Enable memory efficient attention if available
        if hasattr(pipeline, "enable_attention_slicing"):
            pipeline.enable_attention_slicing()
        
        # NOTE: Removed enable_model_cpu_offload() as it causes CPU/GPU shuffling
        # which significantly slows down generation. Keep model fully on GPU for speed.
        
        print("✅ Model loaded successfully!")
        if device == "cuda":
            print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        return pipeline
        
    except Exception as e:
        print(f"❌ Error loading model: {str(e)}")
        print("\n💡 Make sure you have:")
        print("   - Sufficient disk space (model is ~4GB)")
        print("   - Internet connection for first-time download")
        print("   - PyTorch installed correctly")
        raise

def generate_image(prompt: str, num_images: int = 1, negative_prompt: str = None) -> list:
    """
    Generate image(s) from a text prompt using Stable Diffusion
    
    Args:
        prompt: Text description of the image to generate
        num_images: Number of images to generate (default: 1)
        negative_prompt: What to avoid in the image (optional)
    
    Returns:
        List of PIL Image objects
    """
    global pipeline
    
    if pipeline is None:
        pipeline = load_pipeline()
    
    device = get_device()
    generated_images = []
    
    # Default negative prompt for better results
    if negative_prompt is None:
        negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions"
    
    for i in range(num_images):
        try:
            print(f"   Generating image {i+1}/{num_images}...", end="", flush=True)
            
            # Generate image
            with torch.no_grad():
                result = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=NUM_INFERENCE_STEPS,
                    guidance_scale=GUIDANCE_SCALE,
                    num_images_per_prompt=1
                )
            
            image = result.images[0]
            generated_images.append(image)
            print(" ✅")
            
        except Exception as e:
            print(f"\n   ❌ Error generating image: {str(e)}")
            return []
    
    return generated_images

def save_image(image: Image.Image, prompt: str, output_dir: str, index: int = 0) -> str:
    """Save PIL Image to file"""
    try:
        # Create filename from prompt (sanitized)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c for c in prompt[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        
        if index > 0:
            filename = f"{timestamp}_{safe_prompt}_{index}.png"
        else:
            filename = f"{timestamp}_{safe_prompt}.png"
        
        filepath = os.path.join(output_dir, filename)
        
        # Save image
        image.save(filepath, "PNG")
        
        return filepath
    except Exception as e:
        print(f"   ❌ Error saving image: {str(e)}")
        return None

def main():
    """Main interactive loop for image generation"""
    print("=" * 60)
    print("Image Generation Agent - Stable Diffusion")
    print("=" * 60)
    print(f"Model: {STABLE_DIFFUSION_MODEL}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Device: {get_device()}")
    print("\nAvailable capabilities:")
    print("  - Generate images from text prompts")
    print("  - Create multiple variations")
    print("  - Save generated images automatically")
    print("\nType 'exit' or 'quit' to stop\n")
    print("-" * 60)
    
    # Initialize memory system
    memory = AgentMemory()
    message_count = memory.get_message_count()
    if message_count > 0:
        print(f"\n📚 Loaded {message_count} messages from memory")
    
    # Ensure output directory exists
    output_dir = ensure_output_dir()
    print(f"\n✅ Output directory: {output_dir}")
    
    # Load pipeline (this will download model on first run)
    try:
        load_pipeline()
    except Exception as e:
        print(f"\n❌ Failed to load Stable Diffusion model")
        print(f"Error: {str(e)}")
        sys.exit(1)
    
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
            prompt = user_input
            
            # Check for number specification
            if "generate" in user_input.lower() or "x" in user_input.lower():
                parts = user_input.lower().split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i > 0:
                        prev_word = parts[i-1].lower()
                        if prev_word in ["generate", "x", "create", "make"]:
                            num_images = int(part)
                            # Remove number from prompt
                            prompt_parts = user_input.split()
                            prompt_parts.pop(i)
                            prompt = " ".join(prompt_parts)
                            break
            
            # Save user prompt to memory
            memory.add_message("human", f"Generate image: {prompt}")
            
            print(f"\n🖼️  Generating {num_images} image(s)...")
            print(f"   Prompt: {prompt}")
            
            # Generate images
            images = generate_image(prompt, num_images=num_images)
            
            if images:
                print(f"\n✅ Generated {len(images)} image(s)!")
                
                # Save images
                saved_paths = []
                for i, img in enumerate(images):
                    filepath = save_image(img, prompt, output_dir, i if num_images > 1 else 0)
                    if filepath:
                        saved_paths.append(filepath)
                        print(f"   💾 Saved: {filepath}")
                
                # Save response to memory
                response_text = f"Generated {len(images)} image(s) from prompt: {prompt}"
                if saved_paths:
                    response_text += f"\nSaved to: {', '.join(saved_paths)}"
                memory.add_message("ai", response_text)
                
                print(f"\n📁 Images saved to: {output_dir}")
            else:
                print("\n❌ Failed to generate images")
                memory.add_message("ai", f"Failed to generate image from prompt: {prompt}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Try rephrasing your prompt or check the error above.")

if __name__ == "__main__":
    main()
