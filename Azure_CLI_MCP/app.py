#!/usr/bin/env python3
"""
Flask web server for Azure CLI Chat Assistant
Serves the web interface and provides API endpoints for chat functionality
"""

import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import logging

# Import the existing MCP client
from main import MCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Global variables
mcp_client: MCPClient = None
chat_sessions: Dict[str, Any] = {}

def get_or_create_session_id() -> str:
    """Generate a unique session ID for conversation tracking"""
    import uuid
    return str(uuid.uuid4())

async def initialize_mcp_client():
    """Initialize the MCP client connection"""
    global mcp_client
    try:
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
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    global mcp_client
    is_healthy = mcp_client is not None and mcp_client.session is not None
    return jsonify({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'mcp_connected': is_healthy
    }), 200 if is_healthy else 503

@app.route('/api/chat', methods=['POST'])
async def chat():
    """Handle chat messages and return responses"""
    global mcp_client, chat_sessions
    
    try:
        # Parse request
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        message = data['message'].strip()
        if not message:
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
                'message_count': 0
            }
        
        # Check if MCP client is available
        if not mcp_client or not mcp_client.session:
            return jsonify({
                'success': False,
                'error': 'Azure CLI service is not available. Please check your connection.'
            }), 503
        
        # Process the message
        logger.info(f"Processing message for conversation {conversation_id}: {message[:100]}...")
        
        try:
            response = await mcp_client.process_query(message)
            
            # Update session
            chat_sessions[conversation_id]['message_count'] += 1
            chat_sessions[conversation_id]['last_activity'] = datetime.utcnow()
            
            # Generate message ID
            message_id = f"{conversation_id}_{chat_sessions[conversation_id]['message_count']}"
            
            return jsonify({
                'success': True,
                'data': {
                    'response': response,
                    'conversation_id': conversation_id,
                    'message_id': message_id
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

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def clear_conversation(conversation_id: str):
    """Clear a specific conversation"""
    global chat_sessions
    
    if conversation_id in chat_sessions:
        del chat_sessions[conversation_id]
        logger.info(f"Cleared conversation {conversation_id}")
    
    return jsonify({
        'success': True,
        'message': 'Conversation cleared'
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
    
    return jsonify({
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'mcp': mcp_status,
        'active_sessions': len(chat_sessions)
    })

# Static file serving
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

async def startup():
    """Initialize the application"""
    logger.info("Starting Azure CLI Chat Assistant...")
    
    # Initialize MCP client
    success = await initialize_mcp_client()
    if not success:
        logger.warning("MCP client initialization failed - some features may not work")
    
    logger.info("Application startup complete")

def main():
    """Main entry point"""
    import sys
    
    # Set up event loop for Windows
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Initialize async components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(startup())
    
    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    main() 