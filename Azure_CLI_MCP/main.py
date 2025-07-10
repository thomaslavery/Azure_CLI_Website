import asyncio
import json
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


AZURE_TENANT_ID=os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID=os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET=os.getenv("AZURE_CLIENT_SECRET")
AZURE_SUBSCRIPTION_ID=os.getenv("AZURE_SUBSCRIPTION_ID")

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.conversation_history = []
        self.available_tools = []
        self.max_iterations = 10
        self.debug = True  # Enable debug mode
        
        
    def log_debug(self, message: str, data=None):
        """Debug logging helper"""
        if self.debug:
            print(f"[DEBUG] {message}")
            if data is not None:
                try:
                    if isinstance(data, (dict, list)):
                        print(f"[DEBUG] Data: {json.dumps(data, indent=2, default=str)}")
                    else:
                        print(f"[DEBUG] Data: {data}")
                except Exception as e:
                    print(f"[DEBUG] Data (raw): {data}")
                    print(f"[DEBUG] JSON serialization failed: {e}")
        
    async def connect_to_azure_cli_server(self, azure_credentials=None):
        """Connect to the Azure CLI MCP server
        
        Args:
            azure_credentials: Azure credentials JSON string (optional, will use env var if not provided)
        """
        try:
            self.log_debug("Starting Azure CLI MCP server connection...")
            
            # Try to get credentials from parameter first, then environment variable
            if azure_credentials is None:
                azure_credentials = os.getenv('AZURE_CREDENTIALS')
            
            # If still no credentials, try to build from individual env vars
            if not azure_credentials and all([AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID]):
                credentials_dict = {
                    "clientId": AZURE_CLIENT_ID,
                    "clientSecret": AZURE_CLIENT_SECRET,
                    "subscriptionId": AZURE_SUBSCRIPTION_ID,
                    "tenantId": AZURE_TENANT_ID,
                    "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
                    "resourceManagerEndpointUrl": "https://management.azure.com/",
                    "activeDirectoryGraphResourceId": "https://graph.windows.net/",
                    "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
                    "galleryEndpointUrl": "https://gallery.azure.com/",
                    "managementEndpointUrl": "https://management.core.windows.net/"
                }
                azure_credentials = json.dumps(credentials_dict)
            
            if not azure_credentials:
                raise ValueError("Azure credentials are required. Set AZURE_CREDENTIALS environment variable or individual Azure credential env vars (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID)")
            
            # Docker command
            command = "docker"
            args = [
                "run",
                "-i", 
                "--rm",
                "-e", "AZURE_CREDENTIALS",
                "my-azure-cli"
            ]
            env = {"AZURE_CREDENTIALS": azure_credentials}
            
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            self.log_debug("Server parameters created", {
                "command": command, 
                "args": args,
                "env_keys": list(env.keys()) if env else None
            })

            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.log_debug("Transport established")
            
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            self.log_debug("Session created")
            
            await self.session.initialize()
            self.log_debug("Session initialized")

            await self._initialize_tools()
            
        except Exception as e:
            self.log_debug(f"Error during server connection: {str(e)}")
            raise
        
    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""         
        # Add the new user message to conversation history
        self.conversation_history.append({
            "role": "user", 
            "content": query
        })
        
        iteration_count = 0
        
        while iteration_count < self.max_iterations:
            try:
                response = await self._get_response()
                
                if self._has_tool_calls(response):
                    await self._process_tool_calls(response)
                    iteration_count += 1
                else:
                    self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                    })
                    
                    return ''.join([textContent.text for textContent in response.content])
                    
            except Exception as e:
                return f"Error processing query: {str(e), sys.exc_info()[2].tb_lineno}" 
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nAzure CLI MCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        print("Type 'clear' to clear conversation history.")
        print("Type 'debug' to toggle debug mode.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break
                elif query.lower() == 'clear':
                    self.conversation_history = []
                    print("\nConversation history cleared.")
                    continue
                elif query.lower() == 'debug':
                    self.debug = not self.debug
                    print(f"\nDebug mode: {'ON' if self.debug else 'OFF'}")
                    continue

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                self.log_debug(f"Error in chat loop: {str(e)}")
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        try:
            self.log_debug("Starting cleanup...")
            await self.exit_stack.aclose()
            self.log_debug("Cleanup completed")
        except Exception as e:
            self.log_debug(f"Error during cleanup: {str(e)}")
            
    async def _get_response(self):
        response = self.anthropic.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1000,
                        messages=self.conversation_history,
                        tools=self.available_tools
                    )
        return response
        
    def _extract_content(self, response) -> str:
        """Extract text content from Claude's response"""
        content = response.content
        text_content = ""
        
        for block in content:
            if block.type == "text":
                text_content += block.text
        
    async def _initialize_tools(self):
        response = await self.session.list_tools()
        print(await self.session.list_tools())
        self.available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in response.tools]
        
    def _has_tool_calls(self, response):
        content = response.content
        for block in content:
            if block.type == "tool_use":
                return True
        return False
    
    async def _process_tool_calls(self, response):
        content = response.content
        assisstant_content = []
        tool_calls = []
        for block in content:
            if block.type == "text":
                assisstant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls.append({
                        "id": block.id,
                        "type": "tool_use",
                        "name": block.name,
                        "input": block.input
                    })
        
        self.conversation_history.append({
            "role": "assistant",
            "content": assisstant_content + tool_calls
        })
        
        for block in content:
            if block.type == "tool_use":
                result = await self.session.call_tool(block.name, block.input)
                self.conversation_history.append({
                    "role": "user",
                    "content": [{"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": ''.join([textContent.text for textContent in result.content])
                        }]
                })
    
    

async def main():
    client = MCPClient()
    try:
        # Connect to Azure CLI server using Docker
        await client.connect_to_azure_cli_server()
        
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main()) 