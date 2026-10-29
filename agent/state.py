from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # add_messages reducer so graph node responses get appended to existing list of messages for an agent query
    messages: Annotated[list[BaseMessage], add_messages]