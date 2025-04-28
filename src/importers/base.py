import pandas as pd
import logging
import datetime
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVImporter(ABC):
    """
    Abstract base class for CSV importers
    """
    def __init__(self, file_path: str, accounts_file: str):
        """
        Initialize the CSV importer with a file path
        
        Args:
            file_path (str): Path to the CSV file to import
            accounts_file (str): Path to the accounts configuration file
        """
        self.file_path = file_path
        self.account_number: str = ""
        self.account_name: str = ""
        self.account_weight: float = 1.0
        self.transactions_df: Optional[pd.DataFrame] = None
        
        # Define standard column mappings (can be overridden by subclasses)
        self.column_mapping: Dict[str, str] = {
            'date': 'date',
            'description': 'description',
            'amount': 'amount',
            'account': 'account'
        }
        
        # Define required columns for the output
        self.required_columns: List[str] = ['date', 'description', 'amount', 'account']
        
        # Load account mappings
        self._load_account_mappings(accounts_file)
        
    def _load_account_mappings(self, accounts_file: str) -> None:
        """
        Load account mappings from the accounts configuration file
        
        Args:
            accounts_file (str): Path to the accounts configuration file
        """
        try:
            # Handle both absolute and relative paths
            if not os.path.isabs(accounts_file):
                app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                accounts_path = os.path.join(app_root, accounts_file)
                if os.path.exists(accounts_path):
                    accounts_file = accounts_path
            
            with open(accounts_file, 'r') as f:
                accounts_data = json.load(f)
                
            self.account_mappings = {
                account['number']: {
                    'name': account['name'],
                    'weight': account.get('weight', 1.0)
                }
                for account in accounts_data.get('accounts', [])
            }
            
        except Exception as e:
            logger.warning(f"Failed to load account mappings from {accounts_file}: {e}")
            self.account_mappings = {}
            
    def _normalize_account_number(self, account_number: str) -> str:
        """
        Normalize an account number by removing special characters, whitespace and converting to lowercase
        
        Args:
            account_number (str): Account number to normalize
            
        Returns:
            str: Normalized account number
        """
        # Remove all non-alphanumeric characters and convert to lowercase
        return ''.join(c.lower() for c in account_number if c.isalnum())
    
    def _map_account(self, account_number: str) -> Tuple[str, float]:
        """
        Map an account number to its name and weight
        
        Args:
            account_number (str): Account number to map
            
        Returns:
            Tuple[str, float]: Account name and weight
        """
        normalized_number = self._normalize_account_number(account_number)
        for config_number, mapping in self.account_mappings.items():
            if self._normalize_account_number(config_number) == normalized_number:
                return mapping['name'], mapping['weight']
        logger.warning(f"Account number '{account_number}' not found in mappings, using number as name and weight 1.0")
        return account_number, 1.0  # Default to account number and weight 1.0 if not found
    
    def import_csv(self) -> pd.DataFrame:
        """
        Import and parse the CSV file to extract account number and transactions
        
        Returns:
            DataFrame: Standardized transactions DataFrame
        """
        try:
            # Read and parse the file
            self._read_file()
            
            # Extract account number
            self._parse_account_number()
            
            # Map account number to name and weight
            self.account_name, self.account_weight = self._map_account(self.account_number)
            
            # Read and standardize transactions
            self.transactions_df = self._read_transactions()
            self.transactions_df = self._standardize_dataframe(self.transactions_df)
            
            # Apply account weight to amounts
            if 'amount' in self.transactions_df.columns:
                self.transactions_df['amount'] = self.transactions_df['amount'] * self.account_weight
            
            logger.info(f"Successfully imported and standardized {len(self.transactions_df)} transactions")
            return self.transactions_df
            
        except Exception as e:
            logger.error(f"Error importing CSV file: {str(e)}")
            raise
    
    @abstractmethod
    def _read_file(self) -> None:
        """
        Read the file and store its contents in a format suitable for parsing
        """
        pass
    
    @abstractmethod
    def _parse_account_number(self) -> None:
        """
        Parse account number from the file
        """
        pass
    
    @abstractmethod
    def _read_transactions(self) -> pd.DataFrame:
        """
        Read transactions from the file into a DataFrame
        
        Returns:
            DataFrame: Raw transactions DataFrame
        """
        pass
    
    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize the DataFrame by renaming columns and converting data types
        
        Args:
            df (DataFrame): Raw DataFrame from CSV
            
        Returns:
            DataFrame: Standardized DataFrame with required column names
        """
        # Create a copy to avoid modifying the original
        std_df = df.copy()
        
        # Rename columns according to mapping
        column_renames = {}
        for source_col, target_col in self.column_mapping.items():
            if source_col in std_df.columns:
                column_renames[source_col] = target_col
        
        std_df = std_df.rename(columns=column_renames)
        
        # Add account column with account name
        std_df['account'] = self.account_name
        
        # Convert data types
        if 'amount' in std_df.columns:
            std_df['amount'] = pd.to_numeric(std_df['amount'], errors='coerce')
        
        # Keep only required columns
        available_columns = [col for col in self.required_columns if col in std_df.columns]
        std_df = std_df[available_columns]
        
        # Check for missing required columns
        missing_columns = set(self.required_columns) - set(std_df.columns)
        if missing_columns:
            logger.warning(f"Missing required columns: {', '.join(missing_columns)}")
            # Add missing columns with default values
            for col in missing_columns:
                if col == 'date':
                    std_df[col] = datetime.datetime.now().strftime('%d.%m.%Y')
                elif col == 'amount':
                    std_df[col] = 0.0
                else:
                    std_df[col] = ''
        
        return std_df 