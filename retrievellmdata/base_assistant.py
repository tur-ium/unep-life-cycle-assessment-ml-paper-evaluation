"""
Base Assistant class that defines the interface for all LLM assistants
"""
from typing import List, Dict, Any, Optional


class BaseAssistant:
    """Base class for all LLM assistants"""
    
    def __init__(self, model_name: str, maintain_history: bool = True):
        """
        Initialize the base assistant
        
        Args:
            model_name: Name of the model to use
            maintain_history: Whether to maintain conversation history
        """
        self.model_name = model_name
        self.maintain_history = maintain_history
        self.conversation_history = []
        self._initialize_model()
        
    def _initialize_model(self, **kwargs) -> None:
        """Initialize the model - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _initialize_model")
        
    def generate_response(self, prompt: str, temperature: float = 0.0, 
                         max_tokens: int = 4096, clear_history: bool = False) -> str:
        """
        Generate a response from the model
        
        Args:
            prompt: The prompt to send to the model
            temperature: Temperature parameter for generation
            max_tokens: Maximum number of tokens to generate
            clear_history: Whether to clear conversation history before generating
            
        Returns:
            The generated response text
        """
        raise NotImplementedError("Subclasses must implement generate_response")
        
    def clear_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []
        
    def add_to_history(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history
        
        Args:
            role: The role of the message sender (user or assistant)
            content: The content of the message
        """
        if self.maintain_history:
            self.conversation_history.append({"role": role, "content": content})