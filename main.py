
from mcp import Server ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.prebuilt import create_react_agent
from langchain.agents import AgentExecutor
from langchain.agents.agent_toolkits import create_react_agent_toolkit
from langchain.agents.agent_toolkits import create_react_agent_toolkit
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY"))

    
    
server_params = StdioServerParameters()
    command = "npx",
    env = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }
    server = Server(server_params)
    await server.start()

    client = stdio_client()
    session = ClientSession(client, server.mcp_server)
    
    
    