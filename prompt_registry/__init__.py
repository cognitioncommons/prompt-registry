"""prompt-registry - Version-controlled prompt templates with variables."""

from .template import PromptTemplate, VariableSpec
from .registry import PromptRegistry

__version__ = "0.1.0"
__all__ = ["PromptRegistry", "PromptTemplate", "VariableSpec"]
