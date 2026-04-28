import os
from typing import Optional, Dict, Any, List, Union
from openai import OpenAI
from dotenv import load_dotenv

class OpenAIClient:
    """
    A wrapper class for OpenAI API client with common LLM operations.
    Handles authentication and provides methods for text generation.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY in environment variables.
            model: The default model to use for text generation.
        """
        load_dotenv()  # Load environment variables from .env file
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.default_model = model
    
    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using the specified model.
        
        Args:
            prompt: The input prompt for text generation.
            model: The model to use. If not provided, uses the default model.
            temperature: Controls randomness in generation (0.0 to 1.0).
            max_tokens: Maximum number of tokens to generate.
            **kwargs: Additional parameters for the OpenAI API.
            
        Returns:
            The generated text as a string.
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating text: {str(e)}")
