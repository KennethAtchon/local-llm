#!/usr/bin/env python3
"""
Image Analysis Agent using Vision Models
Uses Ollama with LangChain for image understanding and analysis
"""

import os
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.tools.file_management import ReadFileTool
from memory import AgentMemory
from PIL import Image

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        return f"Error encoding image: {str(e)}"

def validate_image_file(image_path: str) -> bool:
    """Check if file is a valid image"""
    try:
        Image.open(image_path)
        return True
    except Exception:
        return False

def create_agent_instance():
    """Create and configure the LangChain agent with image analysis tools"""
    
    # Initialize Ollama with vision model
    llm = ChatOllama(
        model=OLLAMA_VISION_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )
    
    # Define custom tools for image operations
    tools = [
        ReadFileTool(),
        Tool(
            name="list_directory",
            func=lambda path: "\n".join(os.listdir(path)),
            description="List files and directories in a given path. Input should be a directory path."
        ),
        Tool(
            name="get_current_directory",
            func=lambda _: os.getcwd(),
            description="Get the current working directory. No input needed."
        ),
        Tool(
            name="validate_image",
            func=validate_image_file,
            description="Validate if a file path is a valid image file. Input should be a file path."
        ),
    ]
    
    # Create agent using the new API
    system_prompt = """You are a helpful AI assistant specialized in analyzing and understanding images.
You have access to vision models that can see and describe images in detail.

Available capabilities:
- Analyze and describe images
- Answer questions about image content
- Identify objects, people, text, and scenes in images
- Provide detailed visual descriptions

When analyzing images, be thorough and descriptive. Include details about:
- Objects and people present
- Text content (if any)
- Colors, composition, and style
- Context and setting
- Any notable features or details"""
    
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        debug=False,
    )
    
    return agent_graph, tools

def create_image_message(image_path: str, question: str = None) -> HumanMessage:
    """Create a HumanMessage with an image attachment for Ollama vision models"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    if not validate_image_file(image_path):
        raise ValueError(f"File is not a valid image: {image_path}")
    
    # Encode image to base64
    image_base64 = encode_image_to_base64(image_path)
    
    # For Ollama vision models, we need to use the proper format
    # LangChain's ChatOllama supports images via content list
    content = []
    
    # Add text question if provided
    if question:
        content.append({"type": "text", "text": question})
    else:
        content.append({"type": "text", "text": "Describe this image in detail."})
    
    # Add image in the format Ollama expects
    # Using the OpenAI-compatible format that LangChain supports
    content.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{image_base64}"
        }
    })
    
    return HumanMessage(content=content)

def main():
    """Main interactive loop for image analysis"""
    print("=" * 60)
    print("Image Analysis Agent with Vision Models")
    print("=" * 60)
    print(f"Model: {OLLAMA_VISION_MODEL}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print("\nAvailable capabilities:")
    print("  - Analyze and describe images")
    print("  - Answer questions about image content")
    print("  - Identify objects, text, and scenes")
    print("\nUsage: Provide an image path and optionally a question")
    print("Example: 'Analyze this image: /path/to/image.jpg'")
    print("\nType 'exit' or 'quit' to stop\n")
    print("-" * 60)
    
    # Initialize memory system
    memory = AgentMemory()
    message_count = memory.get_message_count()
    if message_count > 0:
        print(f"\n📚 Loaded {message_count} messages from memory")
    
    try:
        agent_graph, tools = create_agent_instance()
    except Exception as e:
        print(f"\n❌ Error connecting to Ollama: {e}")
        print(f"\nMake sure Ollama is running at {OLLAMA_BASE_URL}")
        print(f"Make sure the vision model is available: ollama pull {OLLAMA_VISION_MODEL}")
        sys.exit(1)
    
    print("\n✅ Agent ready!\n")
    
    # Load recent conversation history
    conversation_history = memory.get_recent_messages(limit=50)
    
    while True:
        try:
            user_input = input("\n🖼️  You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Parse input to extract image path and question
            image_path = None
            question = user_input
            
            # Look for image path patterns
            if "image:" in user_input.lower() or "analyze" in user_input.lower():
                # Try to extract image path
                parts = user_input.split()
                for i, part in enumerate(parts):
                    if part.lower() in ["image:", "analyze", "this"] and i + 1 < len(parts):
                        potential_path = parts[i + 1]
                        if os.path.exists(potential_path):
                            image_path = potential_path
                            # Reconstruct question without the path
                            question = " ".join([p for p in parts if p != potential_path and p.lower() not in ["image:", "analyze", "this"]])
                            break
            
            # Also check if user just provided a file path
            if not image_path and os.path.exists(user_input):
                image_path = user_input
                question = "Describe this image in detail."
            
            # Save user message to memory
            memory.add_message("human", user_input)
            
            # Create message with or without image
            if image_path:
                try:
                    user_msg = create_image_message(image_path, question or "Describe this image in detail.")
                    print(f"\n📷 Analyzing image: {image_path}")
                except Exception as e:
                    print(f"\n❌ Error loading image: {e}")
                    # Fallback to text-only message
                    user_msg = HumanMessage(content=user_input)
            else:
                user_msg = HumanMessage(content=user_input)
            
            conversation_history.append(user_msg)
            
            print("\n🤖 Agent: ", end="", flush=True)
            
            # Run agent with image
            response = agent_graph.invoke({"messages": conversation_history})
            
            # Extract the output from the response
            output = None
            if isinstance(response, dict):
                if "messages" in response:
                    messages = response["messages"]
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage):
                            content = msg.content
                            if content:
                                content = content.strip()
                                if content and not content.startswith('{') and not content.startswith('IGHL'):
                                    output = content
                                    break
                    if output is None and messages:
                        last_message = messages[-1]
                        if hasattr(last_message, 'content'):
                            content = last_message.content
                            if content and not content.startswith('{') and not content.startswith('IGHL'):
                                output = content
                elif "output" in response:
                    output = response["output"]
            
            # Print the clean output
            if output:
                lines = output.split('\n')
                seen = set()
                clean_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped and line_stripped not in seen:
                        seen.add(line_stripped)
                        clean_lines.append(line)
                    elif not line_stripped:
                        clean_lines.append(line)
                clean_output = '\n'.join(clean_lines)
                print(clean_output)
                
                # Save AI response to memory and conversation history
                memory.add_message("ai", clean_output)
                conversation_history.append(AIMessage(content=clean_output))
                
                # Keep conversation history manageable
                if len(conversation_history) > 50:
                    conversation_history = conversation_history[-50:]
            elif isinstance(response, str):
                print(response)
                memory.add_message("ai", response)
                conversation_history.append(AIMessage(content=response))
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Try rephrasing your request or check the error above.")

if __name__ == "__main__":
    main()
