#!/usr/bin/env python3
"""
Flask web server for Azure CLI Chat Assistant
Serves the web interface and provides API endpoints for chat functionality
Fixed to handle async operations properly with persistent chat history
"""

import os
import asyncio
import json
import threading
import signal
import sys
import atexit
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging

# Import the existing MCP client
from main import MCPClient

# Configure logging to save to file (rewritten on each run)
log_file = 'azure_chat_assistant.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),  # 'w' mode overwrites the file
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

# Log startup message
logger.info("="*50)
logger.info("Azure CLI Chat Assistant Starting Up")
logger.info(f"Log file: {os.path.abspath(log_file)}")
logger.info("="*50)

app = Flask(__name__, static_folder='website/static', static_url_path='')
CORS(app)

# Global variables
mcp_client: MCPClient = None
chat_sessions: Dict[str, Any] = {}
loop = None
CHAT_HISTORY_FILE = 'chat_history.json'

def save_chat_history():
    """Save chat history to JSON file"""
    try:
        # Convert datetime objects to ISO format strings for JSON serialization
        serializable_sessions = {}
        for session_id, session_data in chat_sessions.items():
            serializable_data = session_data.copy()
            if 'created_at' in serializable_data:
                serializable_data['created_at'] = serializable_data['created_at'].isoformat()
            if 'last_activity' in serializable_data:
                serializable_data['last_activity'] = serializable_data['last_activity'].isoformat()
            serializable_sessions[session_id] = serializable_data
        
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_sessions, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Chat history saved to {CHAT_HISTORY_FILE} ({len(chat_sessions)} sessions)")
        return True
    except Exception as e:
        logger.error(f"Failed to save chat history: {e}")
        return False

def load_chat_history():
    """Load chat history from JSON file"""
    global chat_sessions
    
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                loaded_sessions = json.load(f)
            
            # Convert ISO format strings back to datetime objects
            for session_id, session_data in loaded_sessions.items():
                if 'created_at' in session_data:
                    session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                if 'last_activity' in session_data:
                    session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])
                
                # Ensure messages list exists
                if 'messages' not in session_data:
                    session_data['messages'] = []
            
            chat_sessions = loaded_sessions
            logger.info(f"Chat history loaded from {CHAT_HISTORY_FILE} ({len(chat_sessions)} sessions)")
            
            # Log summary of loaded sessions
            total_messages = sum(len(session.get('messages', [])) for session in chat_sessions.values())
            logger.info(f"Total messages loaded: {total_messages}")
            
        else:
            logger.info(f"No existing chat history file found at {CHAT_HISTORY_FILE}")
            chat_sessions = {}
            
    except Exception as e:
        logger.error(f"Failed to load chat history: {e}")
        chat_sessions = {}

def cleanup_and_exit(signum=None, frame=None):
    """Cleanup function called on exit"""
    logger.info("Cleaning up and saving chat history before exit...")
    
    # Save chat history
    if save_chat_history():
        logger.info("Chat history saved successfully")
    else:
        logger.error("Failed to save chat history on exit")
    
    # Close MCP client if connected
    global mcp_client
    if mcp_client and hasattr(mcp_client, 'session') and mcp_client.session:
        try:
            # Note: We can't easily close async session here, but it should cleanup automatically
            logger.info("MCP client cleanup noted")
        except Exception as e:
            logger.error(f"Error during MCP client cleanup: {e}")
    
    logger.info("Cleanup complete")
    
    # Exit if called by signal
    if signum is not None:
        sys.exit(0)

# Register cleanup function for various exit scenarios
atexit.register(cleanup_and_exit)
signal.signal(signal.SIGINT, cleanup_and_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, cleanup_and_exit)  # Termination signal

def get_or_create_session_id() -> str:
    """Generate a unique session ID for conversation tracking"""
    import uuid
    return str(uuid.uuid4())

def run_async_in_thread(coro):
    """Run async function in the event loop thread"""
    global loop
    if loop is None:
        return None
    
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        return future.result(timeout=30)  # 30 second timeout
    except asyncio.TimeoutError:
        logger.error("Async operation timed out")
        return None
    except Exception as e:
        logger.error(f"Error in async operation: {e}")
        return None

async def initialize_mcp_client():
    """Initialize the MCP client connection"""
    global mcp_client
    try:
        logger.info("Initializing MCP client...")
        mcp_client = MCPClient()
        await mcp_client.connect_to_azure_cli_server()
        logger.info("MCP client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        return False

@app.route('/')
def index():
    """Serve the main chat interface"""
    logger.info("Serving main chat interface")
    return send_from_directory('website/static', 'index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    global mcp_client
    is_healthy = mcp_client is not None and mcp_client.session is not None
    logger.debug(f"Health check: {'healthy' if is_healthy else 'unhealthy'}")
    return jsonify({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'mcp_connected': is_healthy
    }), 200 if is_healthy else 503

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages and return responses"""
    global mcp_client, chat_sessions
    
    try:
        # Parse request
        data = request.get_json()
        if not data or 'message' not in data:
            logger.warning("Chat request missing message")
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        message = data['message'].strip()
        if not message:
            logger.warning("Chat request with empty message")
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400
        
        # Get or create conversation ID
        conversation_id = data.get('conversation_id', get_or_create_session_id())
        
        # Initialize session if needed
        if conversation_id not in chat_sessions:
            chat_sessions[conversation_id] = {
                'created_at': datetime.utcnow(),
                'message_count': 0,
                'messages': []
            }
            logger.info(f"Created new chat session: {conversation_id}")
        
        # Check if MCP client is available
        if not mcp_client or not mcp_client.session:
            logger.error("MCP client not available for chat request")
            return jsonify({
                'success': False,
                'error': 'Azure CLI service is not available. Please check your connection.'
            }), 503
        
        # Process the message using iterative tool call processing
        logger.info(f"Processing message for conversation {conversation_id}: {message[:100]}...")
        
        try:
            # Run the async operation with iterative tool processing
            response = run_async_in_thread(process_query_with_iterative_tools(mcp_client, message))
            
            if response is None:
                logger.error("Failed to get response from MCP client")
                return jsonify({
                    'success': False,
                    'error': 'Failed to process your request - operation timed out or failed'
                }), 500
            
            # Update session with the new message and response
            timestamp = datetime.utcnow()
            chat_sessions[conversation_id]['message_count'] += 1
            chat_sessions[conversation_id]['last_activity'] = timestamp
            
            # Store the message and response in history
            message_pair = {
                'timestamp': timestamp.isoformat(),
                'user_message': message,
                'assistant_response': response,
                'message_id': f"{conversation_id}_{chat_sessions[conversation_id]['message_count']}"
            }
            
            chat_sessions[conversation_id]['messages'].append(message_pair)
            
            # Save chat history after each message
            save_chat_history()
            
            logger.info(f"Successfully processed message {message_pair['message_id']}, response length: {len(response)} chars")
            
            return jsonify({
                'success': True,
                'data': {
                    'response': response,
                    'conversation_id': conversation_id,
                    'message_id': message_pair['message_id']
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to process your request: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

async def process_query_with_iterative_tools(mcp_client, query: str, safety_limit: int = 100) -> str:
    """
    Process a query with unlimited iterative tool call handling.
    This function will continue processing tool calls until no more tool calls are generated.
    
    Args:
        mcp_client: The MCP client instance
        query: The user query to process
        safety_limit: Emergency safety limit to prevent infinite loops (default: 100)
        
    Returns:
        The final response string
    """
    try:
        logger.info(f"Starting unlimited iterative tool processing for query: '{query[:100]}...'")
        
        # Add the new user message to conversation history
        mcp_client.conversation_history.append({
            "role": "user", 
            "content": query
        })

        # Get available tools
        response = await mcp_client.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        
        logger.info(f"Available tools: {[tool['name'] for tool in available_tools]}")

        iteration = 0
        final_text = []
        consecutive_no_tool_responses = 0
        tool_execution_history = []  # Track tool execution for loop detection
        
        while True:
            iteration += 1
            logger.info(f"Tool processing iteration {iteration}")
            
            # Safety check - emergency brake for infinite loops
            if iteration > safety_limit:
                logger.error(f"Emergency stop: Reached safety limit of {safety_limit} iterations")
                final_text.append(f"\n\n[Emergency Stop: Reached safety limit of {safety_limit} iterations]")
                break
            
            # Call Claude API
            try:
                response = mcp_client.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=mcp_client.conversation_history,
                    tools=available_tools
                )
            except Exception as e:
                logger.error(f"Error calling Claude API in iteration {iteration}: {str(e)}")
                final_text.append(f"\n\n[Error: Claude API call failed in iteration {iteration}: {str(e)}]")
                break
            
            logger.info(f"Claude response - content blocks: {len(response.content)}, stop reason: {response.stop_reason}")
            
            # Check if the response contains tool calls
            tool_uses = [content for content in response.content if content.type == 'tool_use']
            text_content = [content for content in response.content if content.type == 'text']
            
            logger.info(f"Iteration {iteration}: Found {len(tool_uses)} tool calls and {len(text_content)} text blocks")
            
            # Add any text content to final output
            for content in text_content:
                final_text.append(content.text)

            if tool_uses:
                # Reset consecutive no-tool counter
                consecutive_no_tool_responses = 0
                
                logger.info(f"Processing {len(tool_uses)} tool calls in iteration {iteration}")
                
                # Track tool calls for potential loop detection
                iteration_tools = [f"{tool_use.name}({json.dumps(tool_use.input, sort_keys=True)})" for tool_use in tool_uses]
                tool_execution_history.append(iteration_tools)
                
                # Simple loop detection - check if we're repeating the exact same tool calls
                if len(tool_execution_history) >= 3:
                    # Check last 3 iterations for identical tool patterns
                    recent_patterns = tool_execution_history[-3:]
                    if recent_patterns[0] == recent_patterns[1] == recent_patterns[2]:
                        logger.warning(f"Detected potential infinite loop: same tools called 3 times in a row")
                        final_text.append(f"\n\n[Warning: Detected potential infinite loop - stopping to prevent endless execution]")
                        break
                
                # Add the assistant's response (with tool uses) to conversation history
                mcp_client.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute all tool calls and collect results
                tool_results = []
                for i, tool_use in enumerate(tool_uses):
                    try:
                        logger.info(f"Executing tool {i+1}/{len(tool_uses)}: {tool_use.name}")
                        
                        result = await mcp_client.session.call_tool(tool_use.name, tool_use.input)
                        
                        # Extract content properly from MCP result
                        if hasattr(result, 'content'):
                            if isinstance(result.content, list):
                                content_text = ""
                                for content_item in result.content:
                                    if hasattr(content_item, 'text'):
                                        content_text += content_item.text
                                    else:
                                        content_text += str(content_item)
                            else:
                                content_text = str(result.content)
                        else:
                            content_text = str(result)
                        
                        logger.info(f"Tool {tool_use.name} executed successfully, result length: {len(content_text)}")
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": content_text
                        })
                        
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_use.name}: {str(e)}")
                        tool_results.append({
                            "type": "tool_result", 
                            "tool_use_id": tool_use.id,
                            "content": f"Error executing tool: {str(e)}"
                        })
                
                # Add all tool results as a single user message
                mcp_client.conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Continue to next iteration to process potential additional tool calls
                logger.info(f"Iteration {iteration} complete, checking for additional tool calls...")
                
            else:
                # No tool calls found
                consecutive_no_tool_responses += 1
                logger.info(f"No tool calls found in iteration {iteration}, consecutive no-tool responses: {consecutive_no_tool_responses}")
                
                # If we get multiple consecutive responses with no tool calls, we're likely done
                if consecutive_no_tool_responses >= 2:
                    logger.info(f"Processing complete: {consecutive_no_tool_responses} consecutive responses with no tool calls")
                    
                    # Add the final response to conversation history
                    mcp_client.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    
                    break
                else:
                    # Add the response to conversation history and continue one more iteration
                    # Sometimes Claude might provide analysis between tool calls
                    mcp_client.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    logger.info("Continuing for one more iteration to ensure no additional tool calls are needed...")
        
        result = "\n".join(final_text)
        logger.info(f"Unlimited iterative tool processing complete after {iteration} iterations, final result length: {len(result)}")
        logger.info(f"Tool execution summary: {len(tool_execution_history)} iterations with tool calls")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in unlimited iterative tool processing: {str(e)}")
        return f"Error processing query with unlimited iterative tools: {str(e)}"

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def clear_conversation(conversation_id: str):
    """Clear a specific conversation"""
    global chat_sessions
    
    if conversation_id in chat_sessions:
        del chat_sessions[conversation_id]
        logger.info(f"Cleared conversation {conversation_id}")
        # Save after clearing
        save_chat_history()
    
    return jsonify({
        'success': True,
        'message': 'Conversation cleared'
    })

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation_history(conversation_id: str):
    """Get conversation history for a specific conversation"""
    global chat_sessions
    
    if conversation_id not in chat_sessions:
        return jsonify({
            'success': False,
            'error': 'Conversation not found'
        }), 404
    
    session = chat_sessions[conversation_id]
    return jsonify({
        'success': True,
        'data': {
            'conversation_id': conversation_id,
            'created_at': session['created_at'].isoformat(),
            'last_activity': session.get('last_activity', session['created_at']).isoformat(),
            'message_count': session['message_count'],
            'messages': session.get('messages', [])
        }
    })

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """List all conversations with metadata"""
    global chat_sessions
    
    conversations = []
    for conv_id, session in chat_sessions.items():
        conversations.append({
            'conversation_id': conv_id,
            'created_at': session['created_at'].isoformat(),
            'last_activity': session.get('last_activity', session['created_at']).isoformat(),
            'message_count': session['message_count'],
            'preview': session.get('messages', [])[-1]['user_message'][:100] + "..." if session.get('messages') else "No messages"
        })
    
    # Sort by last activity (most recent first)
    conversations.sort(key=lambda x: x['last_activity'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': {
            'conversations': conversations,
            'total_count': len(conversations)
        }
    })

@app.route('/api/status')
def get_status():
    """Get detailed system status"""
    global mcp_client, chat_sessions
    
    mcp_status = {
        'connected': mcp_client is not None and mcp_client.session is not None,
        'session_count': len(chat_sessions)
    }
    
    if mcp_client and hasattr(mcp_client, 'conversation_history'):
        mcp_status['conversation_length'] = len(mcp_client.conversation_history)
    
    # Calculate total messages
    total_messages = sum(len(session.get('messages', [])) for session in chat_sessions.values())
    
    logger.info(f"Status request: {len(chat_sessions)} active sessions, {total_messages} total messages, MCP connected: {mcp_status['connected']}")
    
    return jsonify({
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'mcp': mcp_status,
        'active_sessions': len(chat_sessions),
        'total_messages': total_messages,
        'history_file': CHAT_HISTORY_FILE,
        'history_file_exists': os.path.exists(CHAT_HISTORY_FILE)
    })

# Static file serving
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    logger.debug(f"Serving static file: {filename}")
    return send_from_directory('website/static', filename)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory('website/static', 'favicon.ico')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

async def async_startup():
    """Initialize the async components"""
    logger.info("Starting Azure CLI Chat Assistant async components...")
    
    # Initialize MCP client
    success = await initialize_mcp_client()
    if not success:
        logger.warning("MCP client initialization failed - some features may not work")
    
    logger.info("Application async startup complete")

def startup_async_loop():
    """Start the async event loop in a separate thread"""
    global loop
    logger.info("Starting async event loop thread...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_startup())
    
    # Keep the loop running to handle async operations
    logger.info("Async event loop running")
    loop.run_forever()

def main():
    """Main entry point"""
    import sys
    
    logger.info("Azure CLI Chat Assistant main() starting...")
    
    # Load existing chat history
    load_chat_history()
    
    # Start the async event loop in a separate thread
    async_thread = threading.Thread(target=startup_async_loop, daemon=True)
    async_thread.start()
    logger.info("Started async thread")
    
    # Give the async thread time to initialize
    import time
    logger.info("Waiting for async initialization...")
    time.sleep(2)
    
    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting web server on port {port}")
    logger.info(f"Website files served from: website/static/")
    logger.info(f"Chat history file: {os.path.abspath(CHAT_HISTORY_FILE)}")
    logger.info(f"Debug mode: {debug}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        cleanup_and_exit()
    except Exception as e:
        logger.error(f"Server error: {e}")
        cleanup_and_exit()

if __name__ == '__main__':
    main() 