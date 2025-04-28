import re
import pandas as pd
from typing import List
from .base import CSVImporter

class MigrosbankImporter(CSVImporter):
    """
    CSV importer specifically for Migrosbank format
    
    Example format:
    ```
    "Kontoauszug von:";"2025-04-01"
    "Kontoauszug bis:";"2025-04-17"
    ;
    "Vertrag:";"EB12345678"
    "Kontonummer / IBAN:";"12345678 / CH12 3456 7890 1234 5678 90"
    "Bezeichnung:";"Privatkonto"
    "Saldo:";"CHF 1234567890"
    ;
    "Some One"
    "Some Street 123"
    "12345 Some City"
    ;
    ;
    "Datum";"Buchungstext";"Mitteilung";"Referenznummer";"Betrag";"Saldo";"Valuta"
    "01.04.2025";"TWINT Belastung Mustermann, Max, +41 79 123 45 67";"";;"-120,00";"1234567890";"01.04.2025"
    ```
    """
    def __init__(self, file_path: str, accounts_file: str):
        super().__init__(file_path, accounts_file)
        # Override column mappings for Migrosbank format
        self.column_mapping = {
            'Datum': 'date',
            'Buchungstext': 'description',
            'Betrag': 'amount'
        }
        
        self.header_lines: List[str] = []
        self.transactions_start_line = 0
    
    def _read_file(self) -> None:
        """Read the file to find account info and transaction header"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # Find the header row for transactions
            for i, line in enumerate(lines):
                if line.strip().startswith('"Datum";"Buchungstext";"Mitteilung";"Referenznummer";"Betrag";"Saldo";"Valuta"'):
                    self.transactions_start_line = i
                    break
            
            # Store all lines before transactions for account info
            self.header_lines = [line.strip() for line in lines[:self.transactions_start_line] if line.strip()]
    
    def _parse_account_number(self) -> None:
        """Parse account number from header lines"""
        account_number_pattern = r'Kontonummer / IBAN:";"([^/]+)'
        
        for line in self.header_lines:
            # Look for account number
            account_match = re.search(account_number_pattern, line)
            if account_match:
                # Get the raw account number and normalize it
                raw_account = account_match.group(1).strip()
                self.account_number = raw_account
                break  # We only need the account number
    
    def _read_transactions(self) -> pd.DataFrame:
        """Read transactions from CSV, using detected header row"""
        # Read the CSV file with proper settings
        df = pd.read_csv(
            self.file_path, 
            sep=';', 
            skiprows=self.transactions_start_line,  # Skip to the header row
            encoding='utf-8',
            usecols=['Datum', 'Buchungstext', 'Mitteilung', 'Betrag'],
            dtype={
                'Datum': str,
                'Buchungstext': str,
                'Mitteilung': str,
                'Betrag': str
            }
        )
        
        # Clean up the data
        # Remove any rows where all values are NaN
        df = df.dropna(how='all')
        
        # Combine description and message
        df['Buchungstext'] = df['Buchungstext'] + ' ' + df['Mitteilung'].fillna('')
        df = df.drop('Mitteilung', axis=1)
        
        # Convert amount to numeric, replacing comma with dot
        df['Betrag'] = df['Betrag'].str.replace(',', '.').astype(float)
        
        return df 