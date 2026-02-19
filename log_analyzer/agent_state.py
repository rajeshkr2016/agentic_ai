from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # 'add_messages' allows the state to append new messages rather than overwriting
    messages: Annotated[Sequence[BaseMessage], add_messages]
