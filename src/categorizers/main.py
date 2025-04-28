import logging
from typing import Dict, List, Set

from src.categorizers.base import Categorizer
from src.categorizers.keyword import KeywordCategorizer
from src.categorizers.openai import OpenAICategorizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainCategorizer(Categorizer):
    """
    Main categorizer that combines keyword and OpenAI categorization
    Uses keyword matching first, then falls back to OpenAI for unmatched transactions
    """
    def __init__(self, categories: List[str], keyword_rules_file: str, ai_settings_file: str):
        """
        Initialize the main categorizer
        
        Args:
            categories (list): List of categories
            keyword_rules_file (str): Path to the keyword rules file
            ai_settings_file (str): Path to the AI classifier settings file
        """
        super().__init__(categories)
        self.keyword_categorizer = KeywordCategorizer(categories, keyword_rules_file)
        self.openai_categorizer = OpenAICategorizer(categories, ai_settings_file)
        
    def categorize(self, descriptions: Set[str]) -> Dict[str, str]:
        """
        Categorize descriptions using both keyword and OpenAI categorizers
        
        Args:
            descriptions (set): Set of descriptions to categorize
            
        Returns:
            dict: Mapping of descriptions to categories
        """
        # First try keyword matching
        keyword_results = self.keyword_categorizer.categorize(descriptions)
        
        # Find descriptions that couldn't be categorized by keywords
        uncategorized = {desc for desc, cat in keyword_results.items() if cat == "Uncategorized"}
        
        if uncategorized:
            try:
                # Try OpenAI for uncategorized descriptions
                openai_results = self.openai_categorizer.categorize(uncategorized)
                
                # Update results with OpenAI categorizations
                keyword_results.update(openai_results)
            except Exception as e:
                logger.error(f"OpenAI categorizer failed: {e}")
                # Keep the uncategorized results from keyword matching
        
        logger.info(f"Main categorizer completed: {len([cat for cat in keyword_results.values() if cat != 'Uncategorized'])} out of {len(set(descriptions))} transactions categorized")
        logger.info(f"Uncategorized descriptions are: {uncategorized}")
        return keyword_results 