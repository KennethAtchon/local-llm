#!/usr/bin/env python3
"""
Local LLM Agent with File Editing and Web Search - GUI Version
Uses Ollama with LangChain for tool calling with Gradio interface
"""

import os
import sys
from pathlib import Path
import gradio as gr
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools.file_management import ReadFileTool, WriteFileTool
from memory import AgentMemory

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q5_K_M")

# Global agent instance and memory
agent_graph = None
memory = None
conversation_history = []

def create_agent_instance():
    """Create and configure the LangChain agent with tools"""
    
    # Initialize Ollama
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

When using tools, be precise and helpful. For web searches, provide current and relevant information. 
Always give clear, accurate answers based on the tool results."""
    
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        debug=False,
    )
    
    return agent_graph

def chat_with_agent(message, history):
    """Handle chat interaction with the agent"""
    global agent_graph, memory, conversation_history
    
    if agent_graph is None:
        return "❌ Agent not initialized. Please check Ollama connection."
    
    if memory is None:
        return "❌ Memory system not initialized."
    
    try:
        # Save user message to memory
        memory.add_message("human", message)
        
        # Add user message to conversation history
        user_msg = HumanMessage(content=message)
        conversation_history.append(user_msg)
        
        # Run agent using the new LangGraph API with full conversation history
        response = agent_graph.invoke({"messages": conversation_history})
        
        # Extract the output from the response
        output = None
        if isinstance(response, dict):
            if "messages" in response:
                messages = response["messages"]
                # Find the last AIMessage
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        content = msg.content
                        if content:
                            content = content.strip()
                            # Remove tool call artifacts
                            if content and not content.startswith('{') and not content.startswith('IGHL'):
                                output = content
                                break
                # Fallback
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
            
            # Save AI response to memory and conversation history
            memory.add_message("ai", clean_output)
            conversation_history.append(AIMessage(content=clean_output))
            
            # Keep conversation history manageable (last 50 messages)
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
        return f"❌ Error initializing agent: {str(e)}\n\nMake sure Ollama is running at {OLLAMA_BASE_URL}"

def main():
    """Main function to launch the Gradio interface"""
    
    # Initialize agent
    status = initialize_agent()
    
    # Create Gradio interface
    with gr.Blocks(title="Local LLM Agent", theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"""
        # 🤖 Local LLM Agent
        
        **Model:** {OLLAMA_MODEL}  
        **Ollama URL:** {OLLAMA_BASE_URL}
        
        {status}
        
        ### Available Capabilities:
        - 📖 Read files
        - ✏️ Write/edit files
        - 🔍 Search the web
        - 📁 List directories
        """)
        
        chatbot = gr.Chatbot(
            label="Conversation",
            height=500,
            show_copy_button=True
        )
        
        msg = gr.Textbox(
            label="Your Message",
            placeholder="Type your message here...",
            lines=2
        )
        
        with gr.Row():
            submit_btn = gr.Button("Send", variant="primary", scale=1)
            clear_btn = gr.Button("Clear", scale=1)
            refresh_btn = gr.Button("Refresh Agent", scale=1)
        
        status_text = gr.Textbox(
            label="Status",
            value=status,
            interactive=False
        )
        
        def user(user_message, history):
            return "", history + [[user_message, None]]
        
        def bot(history):
            user_message = history[-1][0]
            bot_message = chat_with_agent(user_message, history)
            history[-1][1] = bot_message
            return history
        
        def refresh_agent():
            new_status = initialize_agent()
            return new_status
        
        msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        )
        submit_btn.click(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        )
        clear_btn.click(lambda: None, None, chatbot, queue=False)
        refresh_btn.click(refresh_agent, None, status_text)
        
        gr.Markdown("""
        ### Tips:
        - Ask questions naturally
        - Request file operations: "Read the file README.md"
        - Search the web: "Search for Python best practices"
        - The agent will use tools automatically when needed
        """)
    
    # Launch the interface
    demo.launch(
        server_name="127.0.0.1",  # Only accessible locally
        server_port=7860,
        share=False,  # Set to True if you want a public link
        show_error=True
    )

if __name__ == "__main__":
    main()
