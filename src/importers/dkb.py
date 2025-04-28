import re
import pandas as pd
from typing import List
from .base import CSVImporter

class DKBImporter(CSVImporter):
    """
    CSV importer specifically for DKB format
    
    Example format:
    ```
    "Girokonto";"DE12345678901234567890"
    "Zeitraum:";"17.04.2024 - 17.04.2025"
    "Kontostand vom 19.04.2025:";"1.234,56 €"
    ""
    "Buchungsdatum";"Wertstellung";"Status";"Zahlungspflichtige*r";"Zahlungsempfänger*in";"Verwendungszweck";"Umsatztyp";"IBAN";"Betrag (€)";"Gläubiger-ID";"Mandatsreferenz";"Kundenreferenz"
    "17.04.25";"17.04.25";"Gebucht";"John Doe";"PayPal Europe S.a.r.l. et Cie S.C.A";"1234567890/PP.1234.PP/. Signal Technology Foundation";"Ausgang";"LU12345678901234567890";"-5";"LU12ZZZ0000000000000000123";"12A3456WUEGSG";"1234567890"
    ```
    """
    def __init__(self, file_path: str, accounts_file: str):
        super().__init__(file_path, accounts_file)
        # Override column mappings for DKB format
        self.column_mapping = {
            'Buchungsdatum': 'date',
            'Verwendungszweck': 'description',
            'Betrag (€)': 'amount'
        }
        
        self.header_lines: List[str] = []
        self.transactions_start_line = 0
    
    def _read_file(self) -> None:
        """Read the file to find account info and transaction header"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # Find the header row for transactions
            for i, line in enumerate(lines):
                if line.strip().startswith('"Buchungsdatum";"Wertstellung";"Status";"Zahlungspflichtige*r";"Zahlungsempfänger*in";"Verwendungszweck";"Umsatztyp";"IBAN";"Betrag (€)";"Gläubiger-ID";"Mandatsreferenz";"Kundenreferenz"'):
                    self.transactions_start_line = i
                    break
            
            # Store all lines before transactions for account info
            self.header_lines = [line.strip() for line in lines[:self.transactions_start_line] if line.strip()]
    
    def _parse_account_number(self) -> None:
        """Parse account number from header lines"""
        account_number_pattern = r'Girokonto";"([^"]+)'
        
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
            usecols=['Buchungsdatum', 'Zahlungsempfänger*in', 'Verwendungszweck', 'Betrag (€)'],
            dtype={
                'Buchungsdatum': str,
                'Zahlungsempfänger*in': str,
                'Verwendungszweck': str,
                'Betrag (€)': str
            },
            na_values=['']  # Treat empty strings as NaN
        )
        
        # Clean up the data
        # Remove any rows where all values are NaN
        df = df.dropna(how='all')
        
        # Fill NaN values with empty strings
        df['Zahlungsempfänger*in'] = df['Zahlungsempfänger*in'].fillna('')
        df['Verwendungszweck'] = df['Verwendungszweck'].fillna('')
        
        # Replace dots with spaces in Zahlungsempfänger*in
        df['Zahlungsempfänger*in'] = df['Zahlungsempfänger*in'].str.replace('.', ' ')
        
        # Define keywords that indicate truly unhelpful descriptions
        unhelpful_keywords = [
            'VISA Debitkartenumsatz'
        ]
        
        # Combine Verwendungszweck and Zahlungsempfänger*in, with special handling for PayPal and unhelpful descriptions
        df['Verwendungszweck'] = df.apply(
            lambda row: (
                row['Verwendungszweck'] if 'PayPal' in row['Zahlungsempfänger*in']
                else row['Zahlungsempfänger*in'] if any(keyword in row['Verwendungszweck'] for keyword in unhelpful_keywords)
                else f"{row['Zahlungsempfänger*in']} - {row['Verwendungszweck']}" if row['Verwendungszweck']
                else row['Zahlungsempfänger*in']
            ),
            axis=1
        )
        
        # Ensure description is never empty
        df['Verwendungszweck'] = df['Verwendungszweck'].replace('', 'Unknown Transaction')
        
        # Convert dates from DD.MM.YY to DD.MM.YYYY
        df['Buchungsdatum'] = df['Buchungsdatum'].apply(
            lambda x: f"{x[:6]}20{x[6:]}" if len(x) == 8 else x
        )
        
        # Convert amount to numeric, replacing comma with dot and removing € symbol
        df['Betrag (€)'] = df['Betrag (€)'].str.replace('€', '').str.replace('.', '').str.replace(',', '.').astype(float)
        
        return df 