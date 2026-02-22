"""
model_loader.py
---------------
Generic LLM model loader supporting multiple providers:
  - OpenAI (ChatOpenAI)
  - Anthropic (ChatAnthropic)
  - Azure OpenAI (AzureChatOpenAI)
  - Ollama (ChatOllama) — local models
  - Google Generative AI (ChatGoogleGenerativeAI)
  - Grok / xAI (ChatOpenAI via xAI-compatible endpoint)
  - Groq (ChatGroq — ultra-fast inference)

Usage:
    from model_loader import load_model, create_tool_node

    model, tool_node = load_model(tools=[my_tool_a, my_tool_b])
"""

import os
from typing import Callable

from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode

# Load environment variables before anything else
load_dotenv(override=True, dotenv_path=".env")

# ---------------------------------------------------------------------------
# Supported providers
# ---------------------------------------------------------------------------
SUPPORTED_PROVIDERS = ("openai", "anthropic", "azure", "ollama", "google", "grok", "groq")


def _get_env(key: str, default: str | None = None, required: bool = False) -> str | None:
    """Fetch an env var, optionally raising if missing."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(
            f"Required environment variable '{key}' is not set. "
            "Please add it to your .env file or shell environment."
        )
    return value


# ---------------------------------------------------------------------------
# Provider-specific loaders
# ---------------------------------------------------------------------------

def _load_openai(model_name: str):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("Install langchain-openai: pip install langchain-openai")

    _get_env("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model_name)


def _load_anthropic(model_name: str):
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError("Install langchain-anthropic: pip install langchain-anthropic")

    _get_env("ANTHROPIC_API_KEY", required=True)
    return ChatAnthropic(model=model_name)


def _load_azure(model_name: str):
    try:
        from langchain_openai import AzureChatOpenAI
    except ImportError:
        raise ImportError("Install langchain-openai: pip install langchain-openai")

    _get_env("AZURE_OPENAI_API_KEY", required=True)
    _get_env("AZURE_OPENAI_ENDPOINT", required=True)
    api_version = _get_env("AZURE_OPENAI_API_VERSION", default="2024-02-01")
    return AzureChatOpenAI(
        azure_deployment=model_name,
        api_version=api_version,
    )


def _load_ollama(model_name: str):
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError("Install langchain-ollama: pip install langchain-ollama")

    base_url = _get_env("OLLAMA_BASE_URL", default="http://localhost:11434")
    return ChatOllama(model=model_name, base_url=base_url)


def _load_google(model_name: str):
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "Install langchain-google-genai: pip install langchain-google-genai"
        )

    _get_env("GOOGLE_API_KEY", required=True)
    return ChatGoogleGenerativeAI(model=model_name)


def _load_grok(model_name: str):
    """
    Grok (xAI) uses an OpenAI-compatible API, so we reuse ChatOpenAI
    pointed at xAI's base URL with the XAI_API_KEY.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("Install langchain-openai: pip install langchain-openai")

    api_key = _get_env("XAI_API_KEY", required=True)
    base_url = _get_env("XAI_BASE_URL", default="https://api.x.ai/v1")
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )


def _load_groq(model_name: str):
    """
    Groq uses langchain-groq (ChatGroq) for ultra-fast LPU inference.
    """
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        raise ImportError("Install langchain-groq: pip install langchain-groq")

    _get_env("GROQ_API_KEY", required=True)
    return ChatGroq(model=model_name)


_PROVIDER_LOADERS: dict[str, Callable] = {
    "openai": _load_openai,
    "anthropic": _load_anthropic,
    "azure": _load_azure,
    "ollama": _load_ollama,
    "google": _load_google,
    "grok": _load_grok,
    "groq": _load_groq,
}

# Default model names per provider (used when MODEL_NAME env var is absent)
_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-5-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "azure": "gpt-4o",
    "ollama": "llama3",
    "google": "gemini-2.5-flash",
    "grok": "grok-3",
    "groq": "openai/gpt-oss-120b",
    # "groq": "llama-3.3-70b-versatile",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_model(tools: list | None = None):
    """
    Load an LLM based on environment variables and optionally bind tools.

    Environment Variables
    ---------------------
    LLM_PROVIDER  : One of 'openai', 'anthropic', 'azure', 'ollama', 'google', 'grok', 'groq'.
                    Defaults to 'openai'.
    MODEL_NAME    : Model/deployment name. Falls back to a sensible default per provider.

    Returns
    -------
    tuple[BaseChatModel, ToolNode | None]
        (model_with_tools, tool_node)
        tool_node is None when no tools are supplied.
    """
    tools = tools or []

    provider = _get_env("LLM_PROVIDER", default="openai").lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported provider '{provider}'. "
            f"Choose one of: {', '.join(SUPPORTED_PROVIDERS)}"
        )

    model_name = _get_env("MODEL_NAME", default=_DEFAULT_MODELS[provider])

    loader = _PROVIDER_LOADERS[provider]
    base_model = loader(model_name)

    if tools:
        model = base_model.bind_tools(tools)
        tool_node = ToolNode(tools)
    else:
        model = base_model
        tool_node = None

    print(f"[model_loader] Provider: {provider} | Model: {model_name} | Tools: {len(tools)}")
    return model, tool_node