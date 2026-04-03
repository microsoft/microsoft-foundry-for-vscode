"""AgentServer hosting entrypoint for the Seattle Hotel Agent."""

import argparse
from azure.identity import DefaultAzureCredential
from langgraph.checkpoint.memory import MemorySaver
from starlette.middleware.cors import CORSMiddleware

from azure.ai.agentserver.langgraph import from_langgraph

from agent import create_agent, model, tools

agent_executor = create_agent(model, tools, checkpointer=MemorySaver())

credential = DefaultAzureCredential()
server = from_langgraph(agent_executor, credentials=credential)

# Enable CORS to be used with the Agent Inspector
server.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()
    server.run(port=args.port)
