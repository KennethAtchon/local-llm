#!/usr/bin/env python3
"""
Local LLM Agent with File Editing and Web Search
Uses Ollama with LangChain for tool calling
"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools.file_management import ReadFileTool, WriteFileTool
from memory import AgentMemory
from PIL import Image

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:8b")

# Supported image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}

def validate_image_file(image_path: str) -> bool:
    """Validate that a file path exists and is an image"""
    try:
        path = Path(image_path)
        if not path.exists() or not path.is_file():
            return False
        return path.suffix.lower() in IMAGE_EXTENSIONS
    except Exception:
        return False

def extract_image_paths(text: str) -> list:
    """Extract potential image file paths from text"""
    image_paths = []
    
    # Pattern 1: Quoted paths (single or double quotes)
    quoted_pattern = r'["\']([^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif))["\']'
    matches = re.findall(quoted_pattern, text, re.IGNORECASE)
    image_paths.extend(matches)
    
    # Pattern 2: Absolute paths starting with /
    abs_pattern = r'(/[^\s]+\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif))'
    matches = re.findall(abs_pattern, text, re.IGNORECASE)
    image_paths.extend(matches)
    
    # Pattern 3: Relative paths with ./ or ../
    rel_pattern = r'(\.{0,2}/[^\s]+\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif))'
    matches = re.findall(rel_pattern, text, re.IGNORECASE)
    image_paths.extend(matches)
    
    # Pattern 4: Paths with spaces (common in "analyze this image: path/to/image.jpg")
    space_pattern = r'([^\s]+\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif))'
    matches = re.findall(space_pattern, text, re.IGNORECASE)
    for match in matches:
        if os.path.exists(match) and match not in image_paths:
            image_paths.append(match)
    
    # Validate and return unique valid paths
    valid_paths = []
    for path in image_paths:
        if validate_image_file(path) and path not in valid_paths:
            valid_paths.append(path)
    
    return valid_paths

def load_image(image_path: str) -> Image.Image:
    """Load an image from file path"""
    try:
        return Image.open(image_path)
    except Exception as e:
        raise ValueError(f"Failed to load image from {image_path}: {str(e)}")

def create_agent_instance():
    """Create and configure the LangChain agent with tools"""
    
    # Initialize Ollama without streaming to avoid duplicate output
    # We'll handle output display manually
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )
    
    # Define custom tools
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        DuckDuckGoSearchRun(),
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
    ]
    
    # Create agent using the new API (returns a CompiledStateGraph)
    # Add a system prompt to make the agent more helpful
    system_prompt = """You are a helpful AI assistant with access to tools for:
- Reading and writing files
- Searching the web using DuckDuckGo
- Listing directories
- Getting the current directory
- Analyzing images (when provided)

When using tools, be precise and helpful. For web searches, provide current and relevant information. 
When analyzing images, provide detailed descriptions of what you see. Always give clear, accurate answers based on the tool results."""
    
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        debug=False,  # Disable debug to reduce verbose output
    )
    
    return agent_graph, tools

def main():
    """Main interactive loop"""
    print("=" * 60)
    print("Local LLM Agent with File Editing & Web Search")
    print("=" * 60)
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print("\nAvailable capabilities:")
    print("  - Read files")
    print("  - Write/edit files")
    print("  - Search the web")
    print("  - List directories")
    print("  - Analyze images (provide image path in your message)")
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
        print("Start it with: ollama serve")
        sys.exit(1)
    
    # Create vision model instance for image analysis
    vision_llm = None
    try:
        vision_llm = ChatOllama(
            model=OLLAMA_VISION_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.7,
        )
        print(f"✅ Vision model ready: {OLLAMA_VISION_MODEL}")
    except Exception as e:
        print(f"⚠️  Warning: Could not load vision model ({OLLAMA_VISION_MODEL}): {e}")
        print("   Image analysis will not be available. Install a vision model with:")
        print(f"   ollama pull {OLLAMA_VISION_MODEL}")
    
    print("\n✅ Agent ready!\n")
    
    # Load recent conversation history
    conversation_history = memory.get_recent_messages(limit=50)
    
    while True:
        try:
            user_input = input("\n🤔 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Save user message to memory
            memory.add_message("human", user_input)
            
            # Check for image paths in user input
            image_paths = extract_image_paths(user_input)
            has_images = len(image_paths) > 0 and vision_llm is not None
            
            # Add user message to conversation history
            if has_images:
                # Load images and create message with image content
                image_contents = []
                for img_path in image_paths:
                    try:
                        img = load_image(img_path)
                        image_contents.append(img)
                        print(f"\n📷 Loaded image: {img_path}")
                    except Exception as e:
                        print(f"\n⚠️  Warning: Could not load image {img_path}: {e}")
                
                if image_contents:
                    # Create message with text and images
                    # For LangChain with Ollama, pass images as PIL Image objects in content list
                    content_parts = [user_input] + image_contents
                    
                    user_msg = HumanMessage(content=content_parts)
                    conversation_history.append(user_msg)
                    
                    print("\n🤖 Agent (Vision): ", end="", flush=True)
                    
                    # Use vision model directly for image analysis
                    # Pass only recent messages to avoid token limits
                    recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
                    response = vision_llm.invoke(recent_messages)
                    
                    # Convert response to agent_graph format for consistency
                    if isinstance(response, AIMessage):
                        response = {"messages": [response]}
                    elif hasattr(response, 'content'):
                        response = {"messages": [AIMessage(content=response.content)]}
                    else:
                        response = {"messages": [AIMessage(content=str(response))]}
                else:
                    # No valid images loaded, use regular agent
                    user_msg = HumanMessage(content=user_input)
                    conversation_history.append(user_msg)
                    print("\n🤖 Agent: ", end="", flush=True)
                    response = agent_graph.invoke({"messages": conversation_history})
            else:
                # No images detected, use regular agent
                user_msg = HumanMessage(content=user_input)
                conversation_history.append(user_msg)
                print("\n🤖 Agent: ", end="", flush=True)
                response = agent_graph.invoke({"messages": conversation_history})
            
            # Extract the output from the response
            # The new API returns messages in the response
            output = None
            if isinstance(response, dict):
                if "messages" in response:
                    # Get the last AIMessage which should be the agent's response
                    messages = response["messages"]
                    # Find the last AIMessage (skip HumanMessage and other message types)
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage):
                            # Get clean content, filtering out tool call artifacts
                            content = msg.content
                            if content:
                                # Remove any tool call artifacts that might have leaked through
                                content = content.strip()
                                # Remove any JSON-like tool call remnants
                                if content and not content.startswith('{') and not content.startswith('IGHL'):
                                    output = content
                                    break
                    # Fallback: if no clean AIMessage found, get last message
                    if output is None and messages:
                        last_message = messages[-1]
                        if hasattr(last_message, 'content'):
                            content = last_message.content
                            if content and not content.startswith('{') and not content.startswith('IGHL'):
                                output = content
                        elif isinstance(last_message, dict) and 'content' in last_message:
                            content = last_message['content']
                            if content and not content.startswith('{') and not content.startswith('IGHL'):
                                output = content
                elif "output" in response:
                    output = response["output"]
            
            # Print the clean output
            if output:
                # Remove any duplicate content (sometimes responses get duplicated)
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
                
                # Keep conversation history manageable (last 50 messages)
                if len(conversation_history) > 50:
                    conversation_history = conversation_history[-50:]
            elif isinstance(response, str):
                print(response)
                # Save AI response to memory
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
