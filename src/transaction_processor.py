import json
import logging
import os
from src.categorizers import MainCategorizer
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TransactionProcessor:
    def __init__(self, categories_file: str, keyword_rules_file: str, ai_settings_file: str):
        """
        Initialize the transaction processor
        
        Args:
            categories_file (str): Path to the JSON file with categories
            keyword_rules_file (str): Path to the JSON file with keyword rules
            ai_settings_file (str): Path to the AI classifier settings JSON file
        """
        # Handle both absolute and relative paths
        if not os.path.isabs(categories_file):
            # Try to find the file in the app root directory
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            categories_path = os.path.join(app_root, categories_file)
            if os.path.exists(categories_path):
                categories_file = categories_path
        
        self.categories = self._load_categories(categories_file)
        
        # Initialize the categorizer with the loaded categories and config paths
        self.categorizer = MainCategorizer(
            self.categories,
            keyword_rules_file,
            ai_settings_file
        )
        
    def _load_categories(self, categories_file: str) -> List[str]:
        """
        Load categories from a JSON file
        
        Args:
            categories_file (str): Path to the JSON file with categories
            
        Returns:
            list: List of categories
        """
        try:
            with open(categories_file, 'r') as f:
                data = json.load(f)
            return data.get('categories', [])
        except Exception as e:
            logger.error(f"Error loading categories: {str(e)}")
            return []
    
    def clean_descriptions(self, transactions_df):
        """
        Clean transaction descriptions using regex
        
        Args:
            transactions_df (DataFrame): DataFrame with transactions
            
        Returns:
            DataFrame: DataFrame with cleaned descriptions
        """
        # Pattern to remove card numbers, dates, etc.
        patterns = [
            r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}',  # Remove dates and times
            r'Karte: \d+\*+\d+',                 # Remove card numbers
            r'Betrag: [A-Z]{3} \d+\.\d+',        # Remove amount information
            r'^Einkauf\s+',                      # Remove "Einkauf" if it's the first word
            r'\d+\/PP\.\d+\.PP\/\.',             # Remove Paypal reference numbers
            r'Ihr Einkauf bei',
        ]
        
        # Apply cleaning to the description column directly
        for pattern in patterns:
            transactions_df['description'] = transactions_df['description'].str.replace(pattern, '', regex=True)
        
        # Additional cleaning
        transactions_df['description'] = transactions_df['description'].str.replace(r'\s+', ' ', regex=True)  # Remove multiple spaces
        transactions_df['description'] = transactions_df['description'].str.strip()  # Remove leading/trailing whitespace
            
        logger.info(f"Cleaned {len(transactions_df)} transaction descriptions")
        return transactions_df
    
    def categorize_transactions(self, transactions_df):
        """
        Categorize transactions using the main categorizer
        
        Args:
            transactions_df (DataFrame): DataFrame with transactions
            
        Returns:
            DataFrame: DataFrame with categorized transactions
        """
        # Prepare descriptions for categorization
        descriptions = transactions_df['description'].tolist()
        
        # Use the main categorizer to categorize transactions
        category_mapping = self.categorizer.categorize(set(descriptions))
        
        # Add categories to the DataFrame using the descriptions as keys
        transactions_df["category"] = [category_mapping[desc] for desc in descriptions]
        
        logger.info(f"Successfully categorized {len(descriptions)} transactions")
        
        return transactions_df
    
    def process_transactions(self, transactions_df):
        """
        Process transactions: clean descriptions and categorize
        
        Args:
            transactions_df (DataFrame): DataFrame with transactions
            
        Returns:
            DataFrame: Processed DataFrame with categories
        """
        # Clean descriptions
        cleaned_df = self.clean_descriptions(transactions_df)
        
        # Categorize transactions
        categorized_df = self.categorize_transactions(cleaned_df)
        
        return categorized_df 