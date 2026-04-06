import os
from dotenv import load_dotenv


OPENAI_COMPATIBLE_PROVIDERS = {"openai", "nine_router"}


class ProviderFactory:
    """Factory class for creating LLM providers dynamically."""
    
    @staticmethod
    def create(provider_name: str, model_name: str = None):
        """
        Create an LLM provider instance.
        
        Args:
            provider_name: Name of the provider (openai, gemini, local)
            model_name: Name of the model to use
            
        Returns:
            An LLMProvider instance
            
        Raises:
            ValueError: If provider is not supported
        """
        load_dotenv()
        
        provider_name = provider_name.strip().lower()
        
        if provider_name in OPENAI_COMPATIBLE_PROVIDERS or provider_name == "openai":
            from src.core.openai_provider import OpenAIProvider
            
            if model_name is None:
                model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
            
            api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("BASE_URL")
            
            return OpenAIProvider(
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                provider_name=provider_name,
            )
        
        if provider_name in ["google", "gemini"]:
            from src.core.gemini_provider import GeminiProvider
            
            if model_name is None:
                model_name = "gemini-pro"
            
            api_key = os.getenv("GEMINI_API_KEY")
            return GeminiProvider(
                model_name=model_name,
                api_key=api_key,
            )
        
        if provider_name == "local":
            from src.core.local_provider import LocalProvider
            
            model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
            return LocalProvider(model_path=model_path)
        
        raise ValueError(
            f"Unsupported provider '{provider_name}'. Expected one of: "
            "openai, nine_router, google, gemini, local."
        )


def create_provider():
    """
    Build the configured LLM provider from environment variables.

    Supported providers:
    - openai
    - nine_router (OpenAI-compatible gateway)
    - google
    - local
    """
    load_dotenv()

    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").strip().lower()
    model_name = os.getenv("DEFAULT_MODEL", "gpt-4o").strip()

    return ProviderFactory.create(provider_name, model_name)
