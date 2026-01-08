# gui/app.py
import sys
import os
import time
import traceback
import json
import uuid
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import streamlit as st
from agent.agent_factory import build_agent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Chat History Manager
class ChatHistoryManager:
    """Manages multiple chat sessions with persistent history"""
    
    def __init__(self):
        self.chats_file = "chat_history.json"
        self.load_chats()
    
    def load_chats(self):
        """Load chat history from file"""
        try:
            if os.path.exists(self.chats_file):
                with open(self.chats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    st.session_state.all_chats = data.get('chats', {})
                    st.session_state.chat_metadata = data.get('metadata', {})
            else:
                st.session_state.all_chats = {}
                st.session_state.chat_metadata = {}
        except Exception as e:
            st.session_state.all_chats = {}
            st.session_state.chat_metadata = {}
            print(f"Error loading chat history: {e}")
    
    def save_chats(self):
        """Save chat history to file"""
        try:
            data = {
                'chats': st.session_state.all_chats,
                'metadata': st.session_state.chat_metadata,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.chats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving chat history: {e}")
    
    def create_new_chat(self, title=None):
        """Create a new chat session"""
        chat_id = str(uuid.uuid4())
        if not title:
            title = f"Chat {len(st.session_state.all_chats) + 1}"
        
        st.session_state.all_chats[chat_id] = []
        st.session_state.chat_metadata[chat_id] = {
            'title': title,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'message_count': 0
        }
        
        # Add welcome message
        welcome_msg = {
            "role": "assistant", 
            "content": "⚽ Welcome to Soccerpedia! I'm your AI football assistant. Ask me about matches, players, teams, standings, or any football-related question!",
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.all_chats[chat_id].append(welcome_msg)
        st.session_state.chat_metadata[chat_id]['message_count'] = 1
        
        self.save_chats()
        return chat_id
    
    def add_message(self, chat_id, role, content):
        """Add a message to a chat session"""
        if chat_id not in st.session_state.all_chats:
            return
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        st.session_state.all_chats[chat_id].append(message)
        st.session_state.chat_metadata[chat_id]['last_updated'] = datetime.now().isoformat()
        st.session_state.chat_metadata[chat_id]['message_count'] += 1
        
        # Update title based on first user message
        if role == "user" and st.session_state.chat_metadata[chat_id]['message_count'] == 2:
            # Extract first few words for title
            words = content.split()[:4]
            title = " ".join(words)
            if len(content.split()) > 4:
                title += "..."
            st.session_state.chat_metadata[chat_id]['title'] = title
        
        self.save_chats()
    
    def delete_chat(self, chat_id):
        """Delete a chat session"""
        if chat_id in st.session_state.all_chats:
            del st.session_state.all_chats[chat_id]
            del st.session_state.chat_metadata[chat_id]
            self.save_chats()
    
    def get_chat_summary(self, chat_id):
        """Get a summary of the chat for display"""
        if chat_id not in st.session_state.chat_metadata:
            return "Unknown Chat"
        
        metadata = st.session_state.chat_metadata[chat_id]
        title = metadata.get('title', 'Untitled Chat')
        message_count = metadata.get('message_count', 0)
        last_updated = metadata.get('last_updated', '')
        
        if last_updated:
            try:
                dt = datetime.fromisoformat(last_updated)
                time_str = dt.strftime("%m/%d %H:%M")
            except:
                time_str = "Unknown"
        else:
            time_str = "Unknown"
        
        return f"{title} ({message_count} msgs, {time_str})"

def handle_api_error(error):
    """Handle API errors gracefully"""
    error_str = str(error).lower()
    if "rate limit" in error_str or "429" in error_str:
        return "⚠️ **Rate Limit Exceeded**: The API is temporarily unavailable due to rate limiting. Please wait a moment and try again. You can try asking about different topics or wait 30-60 seconds before making another request."
    elif "401" in error_str or "unauthorized" in error_str:
        return "🔑 **Authentication Error**: There's an issue with the API authentication. Please check the API keys configuration."
    elif "timeout" in error_str:
        return "⏱️ **Timeout Error**: The request took too long to complete. Please try again with a simpler query."
    elif "network" in error_str or "connection" in error_str:
        return "🌐 **Network Error**: Unable to connect to the football data services. Please check your internet connection and try again."
    else:
        return f"❌ **Error**: {str(error)}. Please try rephrasing your question or try again later."

# Page configuration with football theme
st.set_page_config(
    page_title="Soccerpedia - Football Assistant", 
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for football-themed styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    /* Main app styling */
    .stApp {
        background: linear-gradient(135deg, #0d5016 0%, #1e3c20 50%, #0a2c0f 100%);
        font-family: 'Poppins', sans-serif;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        border: 2px solid #fff;
    }
    
    .main-title {
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    .main-subtitle {
        color: #f8f9fa;
        font-size: 1.2rem;
        margin-top: 0.5rem;
        font-weight: 300;
    }
    
    /* Chat container styling */
    .chat-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        border-left: 5px solid #28a745;
    }
    
    /* Loading animation */
    .loading-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
    
    .football-loading {
        width: 60px;
        height: 60px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #28a745;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        position: relative;
    }
    
    .football-loading::before {
        content: "⚽";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 24px;
        animation: bounce 0.5s ease-in-out infinite alternate;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @keyframes bounce {
        0% { transform: translate(-50%, -50%) scale(1); }
        100% { transform: translate(-50%, -50%) scale(1.1); }
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1e3c20 0%, #0d5016 100%);
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 0.75rem;
        font-size: 1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #20c997;
        box-shadow: 0 0 10px rgba(40, 167, 69, 0.3);
    }
    
    /* Message styling */
    .user-message {
        background: linear-gradient(135deg, #007bff, #0056b3);
        color: white;
        padding: 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
    }
    
    .assistant-message {
        background: linear-gradient(135deg, #28a745, #20c997);
        color: white;
        padding: 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem 0;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
    }
    
    /* Error styling */
    .error-message {
        background: linear-gradient(135deg, #dc3545, #c82333);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #ff6b6b;
    }
    
    /* Success styling */
    .success-message {
        background: linear-gradient(135deg, #28a745, #20c997);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #40e0d0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Football-themed header
st.markdown("""
<div class="main-header">
    <h1 class="main-title">⚽ SOCCERPEDIA</h1>
    <p class="main-subtitle">🏆 Your AI-Powered Football Assistant 🏆</p>
    <p style="color: #f8f9fa; font-size: 0.9rem; margin-top: 1rem;">
        💫 Ask about matches, players, teams, standings, and more! 💫
    </p>
</div>
""", unsafe_allow_html=True)

# Initialize chat history manager
if 'chat_manager' not in st.session_state:
    st.session_state.chat_manager = ChatHistoryManager()

# Initialize session states
if 'current_chat_id' not in st.session_state:
    if st.session_state.all_chats:
        # Get the most recent chat
        recent_chat = max(st.session_state.chat_metadata.items(), 
                         key=lambda x: x[1].get('last_updated', ''))
        st.session_state.current_chat_id = recent_chat[0]
    else:
        # Create first chat
        st.session_state.current_chat_id = st.session_state.chat_manager.create_new_chat("Welcome Chat")

if 'quick_query' not in st.session_state:
    st.session_state.quick_query = None

if 'last_request_time' not in st.session_state:
    st.session_state.last_request_time = 0

# Sidebar with chat management and quick actions
with st.sidebar:
    st.markdown("### � Chat Management")
    
    # New chat button
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_id = st.session_state.chat_manager.create_new_chat()
        st.session_state.current_chat_id = new_chat_id
        st.rerun()
    
    # Chat selection
    if st.session_state.all_chats:
        chat_options = {}
        for chat_id in st.session_state.all_chats.keys():
            summary = st.session_state.chat_manager.get_chat_summary(chat_id)
            chat_options[summary] = chat_id
        
        current_summary = st.session_state.chat_manager.get_chat_summary(st.session_state.current_chat_id)
        
        selected_summary = st.selectbox(
            "💭 Select Chat:",
            options=list(chat_options.keys()),
            index=list(chat_options.values()).index(st.session_state.current_chat_id) if st.session_state.current_chat_id in chat_options.values() else 0
        )
        
        if chat_options[selected_summary] != st.session_state.current_chat_id:
            st.session_state.current_chat_id = chat_options[selected_summary]
            st.rerun()
    
    # Delete current chat button (only if more than one chat exists)
    if len(st.session_state.all_chats) > 1:
        if st.button("🗑️ Delete Current Chat", use_container_width=True):
            st.session_state.chat_manager.delete_chat(st.session_state.current_chat_id)
            # Switch to another chat
            remaining_chats = list(st.session_state.all_chats.keys())
            if remaining_chats:
                st.session_state.current_chat_id = remaining_chats[0]
            else:
                st.session_state.current_chat_id = st.session_state.chat_manager.create_new_chat()
            st.rerun()
    
    st.markdown("---")
    st.markdown("### �🚀 Quick Actions")
    
    # Rate limiting info
    if 'last_request_time' in st.session_state:
        time_since_last = time.time() - st.session_state.last_request_time
        if time_since_last < 5:  # 5 second cooldown
            st.warning(f"⏱️ Cooldown: {5 - int(time_since_last)}s remaining")
            can_make_request = False
        else:
            can_make_request = True
    else:
        can_make_request = True
    
    if st.button("🏆 Premier League Standings", use_container_width=True, disabled=not can_make_request):
        if can_make_request:
            st.session_state.quick_query = "Show me the current Premier League standings"
            st.session_state.last_request_time = time.time()
            st.rerun()
    
    if st.button("⚽ Latest PL Results", use_container_width=True, disabled=not can_make_request):
        if can_make_request:
            st.session_state.quick_query = "What are the latest Premier League results?"
            st.session_state.last_request_time = time.time()
            st.rerun()
    
    if st.button("📅 Upcoming Matches", use_container_width=True, disabled=not can_make_request):
        if can_make_request:
            st.session_state.quick_query = "What are the upcoming Premier League matches?"
            st.session_state.last_request_time = time.time()
            st.rerun()
    
    if st.button("🔴 Live Matches", use_container_width=True, disabled=not can_make_request):
        if can_make_request:
            st.session_state.quick_query = "Are there any live matches right now?"
            st.session_state.last_request_time = time.time()
            st.rerun()
    
    if not can_make_request:
        st.info("💡 Rate limiting helps prevent API errors. Please wait a moment between requests.")
    
    st.markdown("---")
    st.markdown("### 📊 Chat Statistics")
    if st.session_state.current_chat_id in st.session_state.chat_metadata:
        current_metadata = st.session_state.chat_metadata[st.session_state.current_chat_id]
        st.metric("Messages in this chat", current_metadata.get('message_count', 0))
        st.metric("Total chats", len(st.session_state.all_chats))
    
    st.markdown("---")
    st.markdown("### 📊 Supported Leagues")
    st.markdown("""
    - 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League (PL)
    - 🇩🇪 Bundesliga (BL1)  
    - 🇮🇹 Serie A (SA)
    - 🇪🇸 La Liga (PD)
    - 🇫🇷 Ligue 1 (FL1)
    - 🏆 Champions League (CL)
    - 🌍 World Cup (WC)
    """)
    
    st.markdown("---")
    st.markdown("### 💡 Example Queries")
    st.markdown("""
    - "Latest Real Madrid results"
    - "Messi's career stats"
    - "Champions League standings"
    - "Transfer news for Arsenal"
    - "Who won the 2018 World Cup?"
    """)

# Initialize agent with error handling
@st.cache_resource
def get_agent():
    """Initialize and cache the football agent"""
    try:
        return build_agent()
    except Exception as e:
        st.error(f"Failed to initialize football agent: {str(e)}")
        return None

# Initialize chat state - load from current chat history
if "messages" not in st.session_state or 'chat_initialized' not in st.session_state:
    # Load messages from current chat
    if st.session_state.current_chat_id in st.session_state.all_chats:
        st.session_state.messages = st.session_state.all_chats[st.session_state.current_chat_id].copy()
    else:
        st.session_state.messages = []
    st.session_state.chat_initialized = True

# Sync messages when chat changes
if st.session_state.get('last_chat_id') != st.session_state.current_chat_id:
    if st.session_state.current_chat_id in st.session_state.all_chats:
        st.session_state.messages = st.session_state.all_chats[st.session_state.current_chat_id].copy()
    else:
        st.session_state.messages = []
    st.session_state.last_chat_id = st.session_state.current_chat_id

if "quick_query" not in st.session_state:
    st.session_state.quick_query = None

if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0

# Function to display loading animation
def show_loading():
    return st.markdown("""
    <div class="loading-container">
        <div class="football-loading"></div>
        <div style="margin-left: 1rem;">
            <p style="color: #28a745; font-weight: 600; margin: 0;">⚽ Processing your request...</p>
            <p style="color: #666; font-size: 0.9rem; margin: 0;">Getting the latest football data</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Function to format messages
def format_message(content, role):
    if role == "user":
        return f'<div class="user-message">👤 <strong>You:</strong><br>{content}</div>'
    else:
        return f'<div class="assistant-message">⚽ <strong>Soccerpedia:</strong><br>{content}</div>'

# Display chat history
for message in st.session_state.messages:
    st.markdown(format_message(message["content"], message["role"]), unsafe_allow_html=True)

# Function to display loading animation
def show_loading():
    return st.markdown("""
    <div class="loading-container">
        <div class="football-loading"></div>
        <div style="margin-left: 1rem;">
            <p style="color: #28a745; font-weight: 600; margin: 0;">⚽ Processing your request...</p>
            <p style="color: #666; font-size: 0.9rem; margin: 0;">Getting the latest football data</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Function to format messages
def format_message(content, role):
    if role == "user":
        return f'<div class="user-message">👤 <strong>You:</strong><br>{content}</div>'
    else:
        return f'<div class="assistant-message">⚽ <strong>Soccerpedia:</strong><br>{content}</div>'

# Display chat history
for message in st.session_state.messages:
    st.markdown(format_message(message["content"], message["role"]), unsafe_allow_html=True)

# Handle quick query
if st.session_state.quick_query:
    prompt = st.session_state.quick_query
    st.session_state.quick_query = None  # Clear after use
    process_query = True
else:
    # Chat input with rate limiting check and placeholder refresh
    prompt = st.chat_input(
        "⚽ Ask about matches, players, teams, or any football question...",
        key=f"chat_input_{st.session_state.current_chat_id}_{len(st.session_state.messages)}"
    )
    
    if prompt:
        # Check rate limiting for manual input
        if 'last_request_time' in st.session_state:
            time_since_last = time.time() - st.session_state.last_request_time
            if time_since_last < 5:  # 5 second cooldown
                st.warning(f"⏱️ Please wait {5 - int(time_since_last)} more seconds before making another request.")
                process_query = False
            else:
                process_query = True
                st.session_state.last_request_time = time.time()
        else:
            process_query = True
            st.session_state.last_request_time = time.time()
    else:
        process_query = False

if prompt and process_query:
    # Add user message to both session and persistent chat
    user_message = {"role": "user", "content": prompt, "timestamp": datetime.now().isoformat()}
    st.session_state.messages.append(user_message)
    st.session_state.chat_manager.add_message(st.session_state.current_chat_id, "user", prompt)
    
    # Display user message immediately
    st.markdown(format_message(prompt, "user"), unsafe_allow_html=True)
    
    # Show loading animation
    loading_placeholder = st.empty()
    with loading_placeholder:
        show_loading()
    
    try:
        # Get agent
        agent = get_agent()
        
        if agent is None:
            raise Exception("Football agent is not available. Please check your configuration.")
        
        # Get response with timeout
        start_time = time.time()
        
        with st.spinner("🔍 Searching football databases..."):
            # Retry mechanism for API calls
            max_retries = 2
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    response = agent.invoke({"input": prompt})
                    answer = response.get("output", "Sorry, I couldn't process your request.")
                    break
                except Exception as retry_error:
                    retry_count += 1
                    if "rate limit" in str(retry_error).lower() and retry_count <= max_retries:
                        st.warning(f"⏳ Rate limit hit, retrying in {retry_count * 2} seconds... (Attempt {retry_count}/{max_retries})")
                        time.sleep(retry_count * 2)  # Exponential backoff
                        continue
                    else:
                        raise retry_error
        
        # Clear loading animation
        loading_placeholder.empty()
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Add response time info for debugging (can be removed in production)
        if response_time > 10:
            answer += f"\n\n*⏱️ Response time: {response_time:.1f}s*"
        
        # Display assistant response
        st.markdown(format_message(answer, "assistant"), unsafe_allow_html=True)
        
        # Add to both session and persistent chat history
        assistant_message = {"role": "assistant", "content": answer, "timestamp": datetime.now().isoformat()}
        st.session_state.messages.append(assistant_message)
        st.session_state.chat_manager.add_message(st.session_state.current_chat_id, "assistant", answer)
        
        # Rerun to refresh the chat input and allow immediate follow-up
        st.rerun()
        
    except Exception as e:
        # Clear loading animation
        loading_placeholder.empty()
        
        # Enhanced error handling
        error_message = "⚠️ **Something went wrong!**\n\n"
        
        if "rate limit" in str(e).lower():
            error_message += "🚫 **Rate Limit Exceeded**: Too many requests. Please wait a moment and try again."
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            error_message += "🌐 **Network Error**: Please check your internet connection and try again."
        elif "api" in str(e).lower():
            error_message += "🔧 **API Error**: There's an issue with our data sources. Please try again in a few minutes."
        elif "timeout" in str(e).lower():
            error_message += "⏰ **Timeout Error**: Your request took too long to process. Please try a simpler query."
        else:
            error_message += f"❌ **Error**: {str(e)}\n\n"
            error_message += "💡 **Suggestions:**\n"
            error_message += "- Try rephrasing your question\n"
            error_message += "- Check if the player/team name is spelled correctly\n"
            error_message += "- Ask about more recent matches or current season data\n"
        
        st.markdown(f'<div class="error-message">{error_message}</div>', unsafe_allow_html=True)
        
        # Add error to both session and persistent chat history
        error_msg = {"role": "assistant", "content": error_message, "timestamp": datetime.now().isoformat()}
        st.session_state.messages.append(error_msg)
        st.session_state.chat_manager.add_message(st.session_state.current_chat_id, "assistant", error_message)
        
        # Rerun to refresh the interface
        st.rerun()
        
        # Log the full error for debugging (in production, use proper logging)
        if st.secrets.get("DEBUG", False):
            with st.expander("🔍 Debug Information (for developers)"):
                st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>⚽ <strong>Soccerpedia</strong> - Powered by AI | 🌟 Built with Streamlit</p>
    <p style="font-size: 0.8rem;">Data sources: Football-Data.org, API-Football, Wikipedia, Transfermarkt</p>
</div>
""", unsafe_allow_html=True)
