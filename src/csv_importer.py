import pandas as pd
import logging
import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from .importers import MigrosbankImporter, DKBImporter
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVImporter(ABC):
    """
    Abstract base class for CSV importers
    """
    def __init__(self, file_path: str):
        """
        Initialize the CSV importer with a file path
        
        Args:
            file_path (str): Path to the CSV file to import
        """
        self.file_path = file_path
        self.account_info: Dict[str, str] = {}
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
        
    def import_csv(self) -> Tuple[Dict[str, str], pd.DataFrame]:
        """
        Import and parse the CSV file to extract account information and transactions
        
        Returns:
            tuple: Account information dictionary and standardized transactions DataFrame
        """
        try:
            # Read and parse the file
            self._read_file()
            
            # Extract account information
            self._parse_account_info()
            
            # Read and standardize transactions
            self.transactions_df = self._read_transactions()
            self.transactions_df = self._standardize_dataframe(self.transactions_df)
            
            logger.info(f"Successfully imported and standardized {len(self.transactions_df)} transactions")
            return self.account_info, self.transactions_df
            
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
    def _parse_account_info(self) -> None:
        """
        Parse account information from the file
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
        
        # Add account column if account name is available
        if 'account_name' in self.account_info:
            std_df['account'] = self.account_info['account_name']
        else:
            std_df['account'] = 'Unknown Account'
        
        # Convert data types
        if 'date' in std_df.columns:
            std_df['date'] = self._convert_date_column(std_df['date'])
        
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
                    std_df[col] = datetime.datetime.now().strftime('%Y-%m-%d')
                elif col == 'amount':
                    std_df[col] = 0.0
                else:
                    std_df[col] = ''
        
        return std_df
    
    def _convert_date_column(self, date_series: pd.Series) -> pd.Series:
        """
        Convert date strings to ISO format (YYYY-MM-DD)
        
        Args:
            date_series (Series): Series containing date strings
            
        Returns:
            Series: Series with ISO formatted date strings
        """
        # Default implementation assumes DD.MM.YY format
        dates = pd.to_datetime(date_series, format='%d.%m.%y', errors='coerce')
        return dates.dt.strftime('%Y-%m-%d')

def get_importer(file_path: str, accounts_file: str):
    """
    Factory function to get the appropriate importer for a file
    
    Args:
        file_path (str): Path to the CSV file
        accounts_file (str): Path to the accounts JSON file
    Returns:
        CSVImporter: An instance of the appropriate importer class
    """
    # Get the filename from the path
    filename = os.path.basename(file_path)
    
    # Use filename patterns to determine the importer
    if "Umsatzliste" in filename:
        return DKBImporter(file_path, accounts_file)
    elif "bookings-export" in filename:
        return MigrosbankImporter(file_path, accounts_file)
    else:
        raise ValueError(f"Could not determine importer for file: {filename}. Expected filename to contain either 'Umsatzliste' or 'bookings-export'")
