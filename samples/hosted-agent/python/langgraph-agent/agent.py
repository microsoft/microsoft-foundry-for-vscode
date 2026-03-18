"""Seattle Hotel Agent — LangGraph implementation.

A travel assistant that helps users find hotels in Seattle.
Uses LangGraph's create_react_agent with a local hotel search tool.

Requires AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME in a .env file.
Uses DefaultAzureCredential for authentication.
"""

import os
from datetime import datetime
from importlib.metadata import version
from typing import Annotated

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

load_dotenv()

endpoint = os.environ["PROJECT_ENDPOINT"]
os.environ["AZURE_AI_PROJECT_ENDPOINT"] = endpoint
deployment_name = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")
openai_endpoint = endpoint.split("/api/projects")[0]

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
model = AzureChatOpenAI(
    model=deployment_name,
    api_version="2024-12-01-preview",
    azure_endpoint=openai_endpoint,
    azure_ad_token_provider=token_provider,
)

# ---------------------------------------------------------------------------
# Simulated hotel data for Seattle
# ---------------------------------------------------------------------------
SEATTLE_HOTELS = [
    {"name": "Contoso Suites", "price_per_night": 189, "rating": 4.5, "location": "Downtown"},
    {"name": "Fabrikam Residences", "price_per_night": 159, "rating": 4.2, "location": "Pike Place Market"},
    {"name": "Alpine Ski House", "price_per_night": 249, "rating": 4.7, "location": "Seattle Center"},
    {"name": "Margie's Travel Lodge", "price_per_night": 219, "rating": 4.4, "location": "Waterfront"},
    {"name": "Northwind Inn", "price_per_night": 139, "rating": 4.0, "location": "Capitol Hill"},
    {"name": "Relecloud Hotel", "price_per_night": 99, "rating": 3.8, "location": "University District"},
]

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def get_available_hotels(
    check_in_date: Annotated[str, "Check-in date in YYYY-MM-DD format"],
    check_out_date: Annotated[str, "Check-out date in YYYY-MM-DD format"],
    max_price: Annotated[int, "Maximum price per night in USD (optional)"] = 500,
) -> str:
    """Get available hotels in Seattle for the specified dates.
    This simulates a call to a fake hotel availability API.
    """
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")

        if check_out <= check_in:
            return "Error: Check-out date must be after check-in date."

        nights = (check_out - check_in).days

        available_hotels = [
            hotel for hotel in SEATTLE_HOTELS if hotel["price_per_night"] <= max_price
        ]

        if not available_hotels:
            return f"No hotels found in Seattle within your budget of ${max_price}/night."

        result = (
            f"Available hotels in Seattle from {check_in_date} to "
            f"{check_out_date} ({nights} nights):\n\n"
        )

        for hotel in available_hotels:
            total_cost = hotel["price_per_night"] * nights
            result += f"**{hotel['name']}**\n"
            result += f"   Location: {hotel['location']}\n"
            result += f"   Rating: {hotel['rating']}/5\n"
            result += f"   ${hotel['price_per_night']}/night (Total: ${total_cost})\n\n"

        return result

    except ValueError as e:
        return f"Error parsing dates. Please use YYYY-MM-DD format. Details: {str(e)}"

# ---------------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTIONS = """You are a helpful travel assistant specializing in finding hotels in Seattle, Washington.

When a user asks about hotels in Seattle:
1. Ask for their check-in and check-out dates if not provided
2. Ask about their budget preferences if not mentioned
3. Use the get_available_hotels tool to find available options
4. Present the results in a friendly, informative way
5. Offer to help with additional questions about the hotels or Seattle

Be conversational and helpful.
If users ask about things outside of Seattle hotels, politely let them know you specialize in Seattle hotel recommendations."""

tools = [get_available_hotels]


def create_agent(llm, agent_tools, checkpointer=None):
    langgraph_version = version("langgraph")
    if langgraph_version < "1.0.0":
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(llm, agent_tools, checkpointer=checkpointer, prompt=SYSTEM_INSTRUCTIONS)
    else:
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(llm, agent_tools, checkpointer=checkpointer, prompt=SYSTEM_INSTRUCTIONS)


agent = create_agent(model, tools)
