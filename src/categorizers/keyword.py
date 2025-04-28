import json
import logging
import os
from typing import Dict, List, Set

from src.categorizers.base import Categorizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KeywordCategorizer(Categorizer):
    """
    Categorizes transactions using keyword matching
    """
    def __init__(self, categories: List[str], keyword_rules_file: str):
        """
        Initialize with categories and keyword rules file
        
        Args:
            categories: List of valid categories
            keyword_rules_file: Path to the keyword rules JSON file
        """
        super().__init__(categories)
        self.keyword_rules = self._load_keyword_rules(keyword_rules_file)
    
    def _load_keyword_rules(self, keyword_rules_file: str) -> Dict[str, List[str]]:
        """
        Load keyword rules from JSON file
        
        Args:
            keyword_rules_file: Path to the keyword rules JSON file
            
        Returns:
            Dictionary mapping categories to lists of keywords
        """
        try:
            # Handle both absolute and relative paths
            if not os.path.isabs(keyword_rules_file):
                app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                rules_path = os.path.join(app_root, keyword_rules_file)
                if os.path.exists(rules_path):
                    keyword_rules_file = rules_path
            
            with open(keyword_rules_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load keyword rules from {keyword_rules_file}: {e}")
            return {}
    
    def categorize(self, descriptions: Set[str]) -> Dict[str, str]:
        """
        Categorize transactions using keyword matching
        
        Args:
            descriptions: Set of transaction descriptions
            
        Returns:
            Dictionary mapping descriptions to categories
        """
        results = {}
        
        for desc in descriptions:
            # Convert description to lowercase for case-insensitive matching
            desc_lower = desc.lower()
            
            # Try to match each category's keywords
            matched = False
            for category, keywords in self.keyword_rules.items():
                if any(keyword.lower() in desc_lower for keyword in keywords):
                    results[desc] = category
                    matched = True
                    break
            
            # If no match found, mark as uncategorized
            if not matched:
                results[desc] = "Uncategorized"
        
        # Log results
        matched_count = len([cat for cat in results.values() if cat != "Uncategorized"])
        logger.info(f"Keyword categorizer matched {matched_count} out of {len(descriptions)} transactions")
        
        return results 