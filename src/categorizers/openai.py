import json
import logging
import os
from collections import defaultdict
from typing import Dict, List, Set

from openai import OpenAI
from src.categorizers.base import Categorizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OpenAICategorizer(Categorizer):
    """
    Categorizes transactions using OpenAI's API with structured output
    """
    def __init__(self, categories: List[str], ai_settings_file: str):
        """
        Initialize with categories and AI settings file
        
        Args:
            categories: List of valid categories
            ai_settings_file: Path to the AI classifier settings JSON file
        """
        # Add uncategorized to categories if it's not already there
        if "Uncategorized" not in categories:
            categories.append("Uncategorized")
        super().__init__(categories)
        
        # Load AI settings
        self.settings = self._load_settings(ai_settings_file)
        self.model = self.settings.get('openai', {}).get('model', 'gpt-4.1-nano')
        self.client = OpenAI(api_key=self.settings.get('openai', {}).get('api_key'))
        self.hints = self.settings.get('category_hints', {})
        
        # Define the JSON schema for structured output
        self.schema = {
            "type": "object",
            "properties": {
                "categorized_transactions": {
                    "type": "array",
                    "description": "List of categorized transactions",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "The transaction description"
                            },
                            "category": {
                                "type": "string",
                                "description": "The assigned category of the transaction",
                                "enum": self.categories
                            }
                        },
                        "required": ["description", "category"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["categorized_transactions"],
            "additionalProperties": False
        }
        
        # Create system message with clear instructions and hints
        self.system_message = f"""
        You are a financial transaction categorization assistant.
        Your task is to analyze each transaction description and assign it to the most appropriate category.
        You must choose exactly one category from the predefined list for each transaction. Use common sense and the hints to make the best decision.
        If you are unsure, assign the transaction to "Uncategorized".
        Keep private TWINT transactions "Uncategorized"
        Available categories:
        {self.categories}
        
        Category Hints:
        {self._format_hints()}
        """
        
    def _load_settings(self, ai_settings_file: str) -> Dict:
        """
        Load AI settings from JSON file
        
        Args:
            ai_settings_file: Path to the AI classifier settings JSON file
            
        Returns:
            Dictionary containing AI settings
        """
        try:
            # Handle both absolute and relative paths
            if not os.path.isabs(ai_settings_file):
                app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                settings_path = os.path.join(app_root, ai_settings_file)
                if os.path.exists(settings_path):
                    ai_settings_file = settings_path
            
            with open(ai_settings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load AI settings from {ai_settings_file}: {e}")
            return {}
            
    def _format_hints(self) -> str:
        """
        Format category hints for the system message
        
        Returns:
            Formatted string of category hints
        """
        if not self.hints:
            return ""
            
        formatted_hints = []
        for category in self.categories:
            if category in self.hints:
                formatted_hints.append(f"- {category}: {self.hints[category]}")
            
        return "\n".join(formatted_hints)
        
    def categorize(self, descriptions: Set[str]) -> Dict[str, str]:
        """
        Categorize transactions using OpenAI
        
        Args:
            descriptions: Set of transaction descriptions
            
        Returns:
            Dictionary mapping descriptions to categories, with "Uncategorized" as default
        """
        if not descriptions:
            return {}
            
        # Process descriptions in batches of 50
        batch_size = 50
        description_list = list(descriptions)
        results = defaultdict(lambda: "Uncategorized")
        
        for i in range(0, len(description_list), batch_size):
            try:
                batch_descriptions = description_list[i:i+batch_size]
                
                # Create transaction objects with description
                transaction_objects = [{"description": desc} for desc in batch_descriptions]
                
                # Send request to OpenAI with structured output
                response = self.client.responses.create(
                    model=self.model,
                    input=[
                        {"role": "system", "content": self.system_message},
                        {"role": "user", "content": f"Please categorize these transactions:\n{json.dumps(transaction_objects, indent=2)}"}
                    ],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "transaction_categorization",
                            "schema": self.schema,
                            "strict": True
                        }
                    }
                )
                
                # Extract the structured response
                response_content = response.output_text
                
                try:
                    categorized_data = json.loads(response_content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response for batch {i//batch_size + 1}: {e}")
                    continue
                
                # Map descriptions to categories
                for item in categorized_data.get("categorized_transactions", []):
                    if "description" in item and "category" in item:
                        results[item["description"]] = item["category"]
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                continue
        
        # Log detailed results if INFO level is enabled
        if logger.isEnabledFor(logging.INFO):
            logger.info("\nOpenAI Categorization Results:")
            logger.info("=" * 50)
            for desc in descriptions:
                logger.info(f"Description: {desc}")
                logger.info(f"Category: {results[desc]}")
                logger.info("-" * 50)
            logger.info(f"\nTotal unique descriptions: {len(descriptions)}")
            logger.info(f"Categorized: {len([x for x in results.values() if x != 'Uncategorized'])}")
            logger.info("=" * 50)
        
        logger.info(f"OpenAI categorizer processed {len(descriptions)} transactions")
        return dict(results)
