import abc
from typing import Dict, List, Set

class Categorizer(abc.ABC):
    """
    Abstract base class for transaction categorizers
    """
    def __init__(self, categories: List[str]):
        """Initialize with a list of valid categories"""
        self.categories = categories
        
    @abc.abstractmethod
    def categorize(self, descriptions: Set[str]) -> Dict[str, str]:
        """
        Categorize a set of transaction descriptions
        
        Args:
            descriptions: Set of transaction descriptions
            
        Returns:
            Dictionary mapping description to category
        """
        pass 