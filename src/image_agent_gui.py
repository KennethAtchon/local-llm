#!/usr/bin/env python3
"""
Image Analysis Agent GUI - Gradio Interface
Uses Ollama vision models for image understanding
"""

import os
import sys
import base64
from pathlib import Path
import gradio as gr
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

# Global agent instance and memory
agent_graph = None
memory = None
conversation_history = []

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
    
    # Define custom tools
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
    
    system_prompt = """You are a helpful AI assistant specialized in analyzing and understanding images.
You have access to vision models that can see and describe images in detail.

Available capabilities:
- Analyze and describe images
- Answer questions about image content
- Identify objects, people, text, and scenes in images
- Provide detailed visual descriptions

When analyzing images, be thorough and descriptive."""
    
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        debug=False,
    )
    
    return agent_graph

def create_image_message(image_path: str, question: str = None) -> HumanMessage:
    """Create a HumanMessage with an image attachment"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    if not validate_image_file(image_path):
        raise ValueError(f"File is not a valid image: {image_path}")
    
    # Encode image to base64
    image_base64 = encode_image_to_base64(image_path)
    
    # Create message with image
    content = []
    if question:
        content.append({"type": "text", "text": question})
    else:
        content.append({"type": "text", "text": "Describe this image in detail."})
    
    content.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{image_base64}"
        }
    })
    
    return HumanMessage(content=content)

def chat_with_image_agent(message, image, history):
    """Handle chat interaction with image analysis"""
    global agent_graph, memory, conversation_history
    
    if agent_graph is None:
        return "❌ Agent not initialized. Please check Ollama connection."
    
    if memory is None:
        return "❌ Memory system not initialized."
    
    try:
        # Save user message to memory
        user_input = message or "Describe this image."
        memory.add_message("human", user_input)
        
        # Create message with or without image
        if image is not None:
            # Gradio provides image as a tuple (image_path, None) or numpy array
            if isinstance(image, tuple):
                image_path = image[0]
            elif isinstance(image, str):
                image_path = image
            else:
                # Save numpy array to temp file
                from PIL import Image as PILImage
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                PILImage.fromarray(image).save(temp_file.name)
                image_path = temp_file.name
            
            try:
                user_msg = create_image_message(image_path, user_input)
            except Exception as e:
                return f"❌ Error loading image: {str(e)}"
        else:
            user_msg = HumanMessage(content=user_input)
        
        conversation_history.append(user_msg)
        
        # Run agent
        response = agent_graph.invoke({"messages": conversation_history})
        
        # Extract output
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
        
        if output:
            # Remove duplicate lines
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
            
            # Save AI response to memory
            memory.add_message("ai", clean_output)
            conversation_history.append(AIMessage(content=clean_output))
            
            # Keep conversation history manageable
            if len(conversation_history) > 50:
                conversation_history = conversation_history[-50:]
            
            return clean_output
        else:
            return "❌ No response from agent."
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

def initialize_agent():
    """Initialize the agent and return status"""
    global agent_graph, memory, conversation_history
    try:
        # Initialize memory system
        memory = AgentMemory()
        message_count = memory.get_message_count()
        
        # Load recent conversation history
        conversation_history = memory.get_recent_messages(limit=50)
        
        # Initialize agent
        agent_graph = create_agent_instance()
        
        status = "✅ Agent initialized successfully!"
        if message_count > 0:
            status += f"\n📚 Loaded {message_count} messages from memory"
        
        return status
    except Exception as e:
        return f"❌ Error initializing agent: {str(e)}\n\nMake sure Ollama is running at {OLLAMA_BASE_URL}\nMake sure vision model is available: ollama pull {OLLAMA_VISION_MODEL}"

def main():
    """Main function to launch the Gradio interface"""
    
    # Initialize agent
    status = initialize_agent()
    
    # Create Gradio interface
    with gr.Blocks(title="Image Analysis Agent", theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"""
        # 🖼️ Image Analysis Agent
        
        **Model:** {OLLAMA_VISION_MODEL}  
        **Ollama URL:** {OLLAMA_BASE_URL}
        
        {status}
        
        ### Available Capabilities:
        - 📷 Analyze and describe images
        - 🔍 Answer questions about image content
        - 🎨 Identify objects, text, and scenes
        - 📝 Provide detailed visual descriptions
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(
                    label="Upload Image",
                    type="filepath",
                    height=400
                )
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="Ask a question about the image, or leave blank for a general description...",
                    lines=2
                )
                submit_btn = gr.Button("Analyze Image", variant="primary", scale=1)
                clear_btn = gr.Button("Clear", scale=1)
                refresh_btn = gr.Button("Refresh Agent", scale=1)
            
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    label="Analysis Results",
                    height=500,
                    show_copy_button=True
                )
        
        status_text = gr.Textbox(
            label="Status",
            value=status,
            interactive=False
        )
        
        def analyze_image(image, question, history):
            if image is None:
                return history, "Please upload an image first."
            
            user_msg = question if question else "Describe this image in detail."
            bot_response = chat_with_image_agent(user_msg, image, history)
            
            if history is None:
                history = []
            
            history.append([f"Image: {os.path.basename(str(image))}\nQuestion: {user_msg}", bot_response])
            return history, ""
        
        def clear_chat():
            return None, ""
        
        def refresh_agent():
            new_status = initialize_agent()
            return new_status
        
        submit_btn.click(
            analyze_image,
            [image_input, question_input, chatbot],
            [chatbot, question_input]
        )
        clear_btn.click(clear_chat, None, [chatbot, question_input])
        refresh_btn.click(refresh_agent, None, status_text)
        
        gr.Markdown("""
        ### Tips:
        - Upload an image using the image input
        - Ask specific questions like "What's in this image?" or "Describe the colors"
        - Leave the question blank for a general description
        - The agent will analyze the image using vision AI models
        """)
    
    # Launch the interface
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,  # Different port from main agent
        share=False,
        show_error=True
    )

if __name__ == "__main__":
    main()
