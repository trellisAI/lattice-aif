#!/usr/bin/env python3
"""
Lattice Client Streamlit GUI - Modern web interface for Lattice CLI
Provides intuitive UI for managing agents, tools, connections, and chat interactions.
"""
import streamlit as st
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import toml
import stat
import time
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="LatticeAIF Client",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        background: linear-gradient(120deg, #1f77b4, #2ecc71);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .feature-card {
        padding: 1.5rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    .stat-card {
        padding: 1.5rem;
        border-radius: 10px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #7f8c8d;
        text-transform: uppercase;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    .assistant-message {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        margin-right: 20%;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .hero-section {
        padding: 3rem 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .quick-action-btn {
        background: white;
        color: #667eea;
        padding: 0.8rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .quick-action-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

DEFAULT_BASE_URL = "http://localhost:44444/"

# Initialize session state
if 'config' not in st.session_state:
    st.session_state.config = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session' not in st.session_state:
    st.session_state.session = None
if 'page' not in st.session_state:
    st.session_state.page = "home"

def get_client_dir() -> Path:
    """Get the client directory path."""
    home = Path.home()
    return home / ".lattice" / "client"

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    client_dir = get_client_dir()
    config_path = client_dir / "config.toml"
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                return toml.load(f)
        except Exception as e:
            st.error(f"Failed to load config: {e}")
            return {}
    return {}

def save_config(url: str, api_key: Optional[str] = None) -> bool:
    """Save configuration to file."""
    client_dir = get_client_dir()
    client_dir.mkdir(parents=True, exist_ok=True)
    config_path = client_dir / "config.toml"
    
    cfg = {"url": url}
    if api_key:
        cfg["api_key"] = api_key
    
    try:
        with config_path.open("w", encoding="utf-8") as f:
            toml.dump(cfg, f)
        config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return True
    except Exception as e:
        st.error(f"Failed to save config: {e}")
        return False

def make_session(api_key: Optional[str] = None, timeout: int = 10) -> requests.Session:
    """Create a requests session with retry logic."""
    s = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    if api_key:
        s.headers.update({"Authorization": f"Bearer {api_key}"})
    s.request_timeout = timeout
    return s

def get_session() -> requests.Session:
    """Get or create session."""
    if st.session_state.session is None:
        config = load_config()
        api_key = config.get("api_key")
        st.session_state.session = make_session(api_key)
    return st.session_state.session

def fetch_agents() -> List[str]:
    """Fetch available agents from the server."""
    try:
        session = get_session()
        config = st.session_state.config
        endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/agents")
        response = session.get(endpoint, timeout=session.request_timeout)
        response.raise_for_status()
        data = response.json()
        print(data)
        # Extract agent IDs - adjust based on actual API response structure
        return data.get('Lattice Agents', [])
    except Exception:
        return []

def fetch_models() -> List[str]:
    """Fetch available models from the server."""
    try:
        session = get_session()
        config = st.session_state.config
        endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/models")
        response = session.get(endpoint, timeout=session.request_timeout)
        response.raise_for_status()
        data = response.json()
        print(data)
        # Extract model names - adjust based on actual API response structure
        return data.get('models', [])
    except Exception:
        return []

# Load config
config = load_config()
st.session_state.config = config

# ==================== SIDEBAR ====================
st.sidebar.markdown('<p class="main-header">🔷 Lattice AIF</p>', unsafe_allow_html=True)
st.sidebar.markdown("---")

#Add HOME and UTILITIES buttons
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🏠 Home"):
        st.session_state.page = "home"
        st.rerun()
with col2:
    if st.button("🛠️ Utilities"):
        st.session_state.page = "utilities"
        st.rerun()
# Configuration Section
with st.sidebar.expander("⚙️ Configuration", expanded=not bool(config)):
    st.markdown("### Connection Settings")
    
    current_url = config.get('url', DEFAULT_BASE_URL)
    current_key = config.get('api_key', '')
    
    url = st.text_input("Server URL", value=current_url, key="config_url")
    api_key = st.text_input("API Key (optional)", value="", type="password", 
                           placeholder="Enter new or leave blank", key="config_key")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save", use_container_width=True):
            if url:
                save_key = api_key if api_key else (current_key if current_key else None)
                if save_config(url, save_key):
                    st.success("✅ Saved!")
                    st.session_state.config = load_config()
                    st.session_state.session = None
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.error("❌ URL required")
    
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            config_path = get_client_dir() / "config.toml"
            if config_path.exists():
                config_path.unlink()
                st.success("✅ Cleared")
                st.session_state.config = {}
                st.session_state.session = None
                time.sleep(0.5)
                st.rerun()


# Status Display
st.sidebar.markdown("### 📊 Status")

#check connection from config
try:
    session = get_session()
    endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/version")
    response = session.get(endpoint, timeout=session.request_timeout)
    response.raise_for_status()
    check_version = True
except Exception:
    check_version = False
if check_version:
    st.sidebar.success("✅ Connected")
    st.sidebar.caption(f"🌐 {config.get('url', 'N/A')}")
    if config.get('api_key'):
        st.sidebar.caption("🔑 API Key Set")
else:
    st.sidebar.error("❌ Not Connected")
    st.sidebar.caption("Set up connection above")

st.sidebar.markdown("---")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")

# ==================== MAIN CONTENT ====================

# Home Page
if st.session_state.page == "home":
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">🚀 Welcome to Lattice AI Platform</h1>
        <p style="font-size: 1.2rem; margin-bottom: 2rem;">
            Your intelligent gateway to AI agents, tools, and seamless automation
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Stats
    if config:
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            session = get_session()
            base_url = config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/"
            
            # Fetch stats
            agents_count = len(fetch_agents())
            models_count = len(fetch_models())
            
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{agents_count}</div>
                    <div class="stat-label">Agents</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{models_count}</div>
                    <div class="stat-label">Models</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">✓</div>
                    <div class="stat-label">Connected</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{len(st.session_state.chat_history)}</div>
                    <div class="stat-label">Chat Messages</div>
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            pass
    
    st.markdown("---")
    
    # Feature Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>💬 Chat Interface</h3>
            <p>Engage with AI agents in real-time conversations with full context awareness</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Start Chatting", key="goto_chat", use_container_width=True):
            st.session_state.page = "utilities"
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>🤖 Agent Management</h3>
            <p>Create, configure, and deploy intelligent agents with custom tools</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⚙️ Manage Agents", key="goto_agents", use_container_width=True):
            st.session_state.page = "utilities"
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>🔧 Tool Integration</h3>
            <p>Connect external tools and services to enhance agent capabilities</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🛠️ Explore Tools", key="goto_tools", use_container_width=True):
            st.session_state.page = "utilities"
            st.rerun()
    
    st.markdown("---")
    
    # Getting Started
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🎯 Getting Started")
        st.markdown("""
        #### Quick Setup Guide
        
        1. **Configure Connection** 📡
           - Set your Lattice server URL in the sidebar
           - Add API key for secure access (optional)
        
        2. **Explore Agents** 🤖
           - Browse available AI agents
           - Create custom agents with specific tools
        
        3. **Start Chatting** 💬
           - Select an agent and model
           - Begin your AI-powered conversation
        
        4. **Integrate Tools** 🔧
           - Add tool servers
           - Configure agent capabilities
        """)
    
    with col2:
        st.markdown("### 📚 Resources")
        st.info("""
        **Documentation**  
        Learn about agent creation, tool integration, and best practices
        
        **API Reference**  
        Explore endpoints and integration options
        
        **Community**  
        Join discussions and share experiences
        """)
        
        st.markdown("### 🆕 What's New")
        st.success("""
        ✨ **v1.0.0**
        - Interactive chat interface
        - Agent management
        - Tool server integration
        - Real-time updates
        """)

# Utilities Page
else:
    st.markdown('<p class="main-header">🛠️ Lattice Utilities</p>', unsafe_allow_html=True)
    
    if not config:
        st.warning("⚠️ Please configure your connection in the sidebar first")
        st.stop()
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "💬 Chat", "🔌CONNECTIONS", "📊 Models", "🤖 Agents", "📝 Prompts", "🛠️ Tool Servers", 
        "🔧 Tools", "🗄️ RAG", "🔗 MCP"
    ])
    
    # ==================== CHAT TAB ====================
    with tab1:
        st.markdown("### 💬 Interactive Chat")
        
        # Fetch available agents and models
        available_agents = fetch_agents()
        available_models = fetch_models()
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if available_agents:
                agent = st.selectbox("Select Agent", available_agents, key="chat_agent")
            else:
                agent = st.text_input("Agent Name", placeholder="Enter agent name", key="chat_agent_manual")
                st.caption("⚠️ No agents found - enter manually or create one in the Agents tab")
        
        with col2:
            if available_models:
                llm = st.selectbox("Select Model", available_models, key="chat_model")
            else:
                llm = st.text_input("Model Name", placeholder="e.g., gpt-4", key="chat_model_manual")
                st.caption("⚠️ No models found - enter manually or check connections")
        
        with col3:
            st.markdown("###")
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        
        st.markdown("---")
        
        # Chat container
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>👤 You</strong><br>{content}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <strong>🤖 Assistant</strong><br>{content}
                    </div>
                    """, unsafe_allow_html=True)
        
        # Chat input
        user_input = st.chat_input("Type your message here...")
        
        if user_input and agent and llm:
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Make API call
            try:
                with st.spinner("🤔 Thinking..."):
                    session = get_session()
                    endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/chat")
                    payload = {
                        "agent": agent,
                        "model": llm,
                        "messages": [{"role": "user", "content": user_input}]
                    }
                    
                    response = session.post(endpoint, json=payload, timeout=session.request_timeout)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extract response
                    if "choices" in data and len(data["choices"]) > 0:
                        assistant_msg = data["choices"][0]["message"]["content"]
                        st.session_state.chat_history.append({"role": "assistant", "content": assistant_msg})
                    
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        elif user_input:
            st.warning("⚠️ Please select both agent and model")
    
    # ==================== CONNECTIONS TAB ====================
    with tab2:
        st.markdown("### Manage Connections")
    
        if st.button("🔄 Refresh Connections", use_container_width=True):
            st.rerun()
        
        if config:
            try:
                session = get_session()
                endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/connections")
                response = session.get(endpoint, timeout=session.request_timeout)
                response.raise_for_status()
                connections = response.json()
                
                if connections:
                    if isinstance(connections, dict):
                        st.markdown(f"**Active:** {len(connections)}")
                    elif isinstance(connections, list):
                        st.markdown(f"**Active:** {len(connections)}")
                    with st.expander("View Details"):
                        st.json(connections)
                else:
                    st.info("No connections")
            except Exception as e:
                st.error(f"Error: {str(e)[:50]}...")
        else:
            st.warning("Configure first")

        st.sidebar.markdown("---")
    
    # ==================== MODELS TAB ====================
    with tab3:
        st.markdown("### 📊 Models")
        st.info("ℹ️ Models are auto-loaded from connections")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key="refresh_models", use_container_width=True):
                st.rerun()
        
        try:
            session = get_session()
            endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/models")
            response = session.get(endpoint, timeout=session.request_timeout)
            response.raise_for_status()
            models = response.json()
            
            if models:
                st.json(models)
            else:
                st.info("📭 No models found")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    # ==================== AGENTS TAB ====================
    with tab4:
        st.markdown("### 🤖 Agent Management")
        
        subtab1, subtab2, subtab3 = st.tabs(["📋 List", "➕ Add", "✏️ Edit"])
        
        with subtab1:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Refresh", key="refresh_agents", use_container_width=True):
                    st.rerun()
            
            try:
                session = get_session()
                endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/agents")
                response = session.get(endpoint, timeout=session.request_timeout)
                response.raise_for_status()
                agents = response.json()
                
                if agents:
                    st.json(agents)
                else:
                    st.info("📭 No agents found")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        
        with subtab2:
            with st.form("add_agent_form"):
                agent_id = st.text_input("Agent ID", placeholder="my-agent")
                prompt = st.text_input("Prompt Name (optional)", placeholder="default-prompt")
                tool_file = st.text_input("Tool Function File", placeholder="tools.json")
                
                st.info("💡 Place tool files in ~/.lattice/client/tools/")
                
                submit = st.form_submit_button("➕ Create Agent", use_container_width=True)
                
                if submit and agent_id and tool_file:
                    try:
                        tools_path = get_client_dir() / "tools" / tool_file
                        
                        if not tools_path.exists():
                            st.error(f"❌ Tool file not found: {tool_file}")
                        else:
                            with tools_path.open("r", encoding="utf-8") as f:
                                tool_json = json.load(f)
                            
                            for tool in tool_json:
                                tool["details"] = {"action": "rephrase"}
                            
                            payload = {
                                "id": agent_id,
                                "prompt": prompt if prompt else None,
                                "tools": tool_json
                            }
                            
                            session = get_session()
                            endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/agents")
                            response = session.post(endpoint, json=payload, timeout=session.request_timeout)
                            response.raise_for_status()
                            
                            # Save locally
                            agents_dir = get_client_dir() / "agents"
                            agents_dir.mkdir(parents=True, exist_ok=True)
                            with (agents_dir / f"{agent_id}_config.json").open("w", encoding="utf-8") as f:
                                json.dump(payload, f, indent=4)
                            
                            st.success(f"✅ Agent '{agent_id}' created!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        with subtab3:
            st.info("Select an agent to edit (coming soon)")
    
    # ==================== PROMPTS TAB ====================
    with tab5:
        st.markdown("### 📝 Prompt Management")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key="refresh_prompts", use_container_width=True):
                st.rerun()
        
        try:
            session = get_session()
            endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/prompts")
            response = session.get(endpoint, timeout=session.request_timeout)
            response.raise_for_status()
            prompts = response.json()
            
            if prompts:
                st.json(prompts)
            else:
                st.info("📭 No prompts found")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    # ==================== TOOL SERVERS TAB ====================
    with tab6:
        st.markdown("### 🛠️ Tool Server Management")
        
        subtab1, subtab2 = st.tabs(["📋 List", "➕ Add"])
        
        with subtab1:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Refresh", key="refresh_toolservers", use_container_width=True):
                    st.rerun()
            
            try:
                session = get_session()
                endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/toolserver")
                response = session.get(endpoint, timeout=session.request_timeout)
                response.raise_for_status()
                servers = response.json()
                
                if servers:
                    st.json(servers)
                else:
                    st.info("📭 No tool servers found")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        
        with subtab2:
            with st.form("add_toolserver"):
                name = st.text_input("Tool Server Name")
                url = st.text_input("Tool Server URL")
                details = st.text_area("Additional Details (JSON, optional)")
                
                submit = st.form_submit_button("➕ Add Server", use_container_width=True)
                
                if submit and name and url:
                    try:
                        payload = {"id": name, "url": url, "details": {}}
                        if details:
                            payload["details"] = json.loads(details)
                        
                        session = get_session()
                        endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/toolserver")
                        response = session.post(endpoint, json=payload, timeout=session.request_timeout)
                        response.raise_for_status()
                        
                        st.success(f"✅ Tool server '{name}' added!")
                        time.sleep(1)
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON in details")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # ==================== TOOLS TAB ====================
    with tab7:
        st.markdown("### 🔧 Tools Management")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key="refresh_tools", use_container_width=True):
                st.rerun()
        
        try:
            session = get_session()
            endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/tools")
            response = session.get(endpoint, timeout=session.request_timeout)
            response.raise_for_status()
            tools = response.json()
            
            if tools:
                st.json(tools)
            else:
                st.info("📭 No tools found")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    # ==================== RAG TAB ====================
    with tab8:
        st.markdown("### 🗄️ RAG Resources")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key="refresh_rag", use_container_width=True):
                st.rerun()
        
        try:
            session = get_session()
            endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/rag")
            response = session.get(endpoint, timeout=session.request_timeout)
            response.raise_for_status()
            rag = response.json()
            
            if rag:
                st.json(rag)
            else:
                st.info("📭 No RAG resources found")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    # ==================== MCP TAB ====================
    with tab9:
        st.markdown("### 🔗 MCP Resources")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key="refresh_mcp", use_container_width=True):
                st.rerun()
        
        try:
            session = get_session()
            endpoint = urljoin(config.get('url', DEFAULT_BASE_URL).rstrip("/") + "/", "api/lattice/mcp")
            response = session.get(endpoint, timeout=session.request_timeout)
            response.raise_for_status()
            mcp = response.json()
            
            if mcp:
                st.json(mcp)
            else:
                st.info("📭 No MCP resources found")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")