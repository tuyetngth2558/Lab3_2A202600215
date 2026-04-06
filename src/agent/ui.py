import streamlit as st
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.provider_factory import ProviderFactory
from src.agent.agent import ReActAgent
from src.tools.registry import get_tools

# Page config
st.set_page_config(
    page_title="ReAct Agent UI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 ReAct Agent Assistant")
st.markdown("*An intelligent agent that thinks, acts, and observes*")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Provider selection
    provider = st.selectbox(
        "Select LLM Provider:",
        ["openai", "gemini", "local"],
        help="Choose which LLM provider to use"
    )
    
    # API Key setup
    st.subheader("🔑 API Keys")
    
    if provider == "openai":
        api_key_env = os.getenv("OPENAI_API_KEY", "")
        api_key_input = st.text_input(
            "OpenAI API Key:",
            value=api_key_env,
            type="password",
            help="Get your key from https://platform.openai.com/api-keys"
        )
        if api_key_input:
            os.environ["OPENAI_API_KEY"] = api_key_input
        elif not api_key_env:
            st.warning("⚠️ OpenAI API key not set. Please provide one above.")
    
    elif provider == "gemini":
        api_key_env = os.getenv("GEMINI_API_KEY", "")
        api_key_input = st.text_input(
            "Gemini API Key:",
            value=api_key_env,
            type="password",
            help="Get your key from https://makersuite.google.com/app/apikey"
        )
        if api_key_input:
            os.environ["GEMINI_API_KEY"] = api_key_input
        elif not api_key_env:
            st.warning("⚠️ Gemini API key not set. Please provide one above.")
    
    # Model selection based on provider
    st.subheader("🤖 Model Selection")
    if provider == "openai":
        model = st.selectbox("Model:", ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"])
    elif provider == "gemini":
        model = st.selectbox("Model:", ["gemini-pro", "gemini-1.5-pro"])
    else:
        model = st.text_input("Model name:", value="local-model")
        model_path = st.text_input(
            "Model path:",
            value=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"),
            help="Path to the GGUF model file"
        )
        if model_path:
            os.environ["LOCAL_MODEL_PATH"] = model_path
    
    # Max steps
    st.subheader("⚙️ Agent Settings")
    max_steps = st.slider(
        "Max Steps:",
        min_value=1,
        max_value=15,
        value=5,
        help="Maximum number of thought-action-observation cycles"
    )
    
    st.divider()
    st.markdown("### Available Tools:")
    tools = get_tools()
    for tool in tools:
        st.markdown(f"- **{tool['name']}**: {tool['description']}")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "current_provider" not in st.session_state:
        st.session_state.current_provider = None
    if "initialization_error" not in st.session_state:
        st.session_state.initialization_error = None

    # Check if we have required API key
    api_key_available = True
    error_message = None
    
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        api_key_available = False
        error_message = "❌ OpenAI API key is required. Please enter it in the sidebar."
    elif provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        api_key_available = False
        error_message = "❌ Gemini API key is required. Please enter it in the sidebar."

    # Re-initialize agent if provider changed or API key was provided
    if api_key_available and (st.session_state.current_provider != provider or st.session_state.agent is None):
        try:
            llm_provider = ProviderFactory.create(provider, model)
            tools = get_tools()
            st.session_state.agent = ReActAgent(llm_provider, tools, max_steps=max_steps)
            st.session_state.current_provider = provider
            st.session_state.initialization_error = None
            st.success(f"✅ Agent initialized with {provider.upper()} provider (model: {model})")
        except Exception as e:
            st.session_state.initialization_error = str(e)
            st.error(f"❌ Error initializing agent: {str(e)}")
            if "api_key" in str(e).lower():
                st.info("💡 Make sure your API key is set in the sidebar above.")
    
    if error_message:
        st.warning(error_message)

    # Display chat history
    if st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "steps" in message:
                    with st.expander("📋 View reasoning steps"):
                        for i, step in enumerate(message["steps"], 1):
                            st.markdown(f"**Step {i}:**")
                            st.markdown(step)
                            st.divider()

    # Input area
    if api_key_available and st.session_state.agent:
        user_input = st.chat_input("Ask the agent something...", key="user_input")
        
        if user_input:
            # Add user message to history
            st.session_state.messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Display user message
            with st.chat_message("user"):
                st.write(user_input)
            
            # Get agent response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Agent is thinking..."):
                    try:
                        response = st.session_state.agent.run(user_input)
                        st.write(response)
                        
                        # Store response with reasoning steps
                        steps = []
                        if st.session_state.agent.history:
                            for item in st.session_state.agent.history:
                                step_text = f"**Thought & Action:**\n{item.get('thought_action', 'N/A')}\n\n**Observation:**\n{item.get('observation', 'N/A')}"
                                steps.append(step_text)
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "steps": steps
                        })
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
    else:
        if not api_key_available:
            st.info("👆 Please enter your API key in the sidebar to get started.")
        elif st.session_state.initialization_error:
            st.warning("⚠️ Agent not initialized. Check the error message and sidebar configuration.")
        else:
            st.info("⚙️ Configuring agent...")

with col2:
    st.subheader("📊 Session Info")
    
    if st.session_state.messages:
        user_msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        st.metric("User Messages", user_msg_count)
    
    st.metric("Provider", provider.upper())
    st.metric("Model", model)
    st.metric("Max Steps", max_steps)
    
    st.divider()
    
    if st.button("🔄 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    if st.button("🗑️ Reset Agent", use_container_width=True):
        st.session_state.agent = None
        st.session_state.messages = []
        st.session_state.current_provider = None
        st.session_state.initialization_error = None
        st.rerun()

st.divider()
st.markdown("""
### 🎯 How it works:
1. **Configure** your LLM provider and API key in the sidebar
2. **Ask** the agent any question
3. **Watch** as the agent thinks, uses tools, and reasons
4. **View** the full reasoning process by expanding the steps

The agent uses a ReAct (Reasoning + Acting) pattern to break down complex tasks.

### 📝 Setup Tips:
- **OpenAI**: Get your API key from https://platform.openai.com/api-keys
- **Gemini**: Get your API key from https://makersuite.google.com/app/apikey
- **Local**: Ensure the model file exists at the specified path
""")
