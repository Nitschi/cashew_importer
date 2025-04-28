import json
import logging
import urllib.parse
import smtplib
from email.message import EmailMessage
import re
from datetime import datetime
import socket
import ssl

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AppLinkExporter:
    def __init__(self, base_url="https://cashewapp.web.app", email_settings_file=None):
        """
        Initialize the app link exporter
        
        Args:
            base_url (str): Base URL for the Cashew app
            email_settings_file (str): Path to the email settings JSON file
        """
        self.base_url = base_url
        self.email_settings_file = email_settings_file
        self.email_settings = None
        if email_settings_file:
            self._load_email_settings()
    
    def _load_email_settings(self):
        """Load email settings from the configuration file"""
        try:
            with open(self.email_settings_file, 'r') as f:
                self.email_settings = json.load(f)
            logger.info(f"Loaded email settings from {self.email_settings_file}")
        except Exception as e:
            logger.error(f"Failed to load email settings from {self.email_settings_file}: {str(e)}")
            self.email_settings = None
    
    def _format_amount(self, amount):
        """
        Format amount to match Cashew's requirements
        
        Args:
            amount: Numeric amount
            
        Returns:
            str: Formatted amount string
        """
        # Convert to float first to handle any string inputs
        amount = float(amount)
        # Format with 2 decimal places and ensure negative sign for expenses
        return f"{amount:.2f}"
    
    def _format_date(self, date_str):
        """
        Format date to match Cashew's requirements (dd.mm.yyyy)
        
        Args:
            date_str: Date string in dd.mm.yyyy format
            
        Returns:
            str: Formatted date string
        """
        # Verify the date is in dd.mm.yyyy format
        if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str):
            logger.warning(f"Date format {date_str} may not be compatible with Cashew")
        return date_str
    
    def create_app_link(self, transactions_df):
        """
        Create a Cashew app link from the processed transactions
        
        Args:
            transactions_df (DataFrame): DataFrame with processed transactions
            
        Returns:
            str: Cashew app link
        """
        # Prepare data for app link
        transactions_data = []

        logger.info("\nSummary:")
        logger.info("=" * 80)
        logger.info(f"{'Date':<12} {'Amount':>10} {'Category':<20} {'Description'}")
        logger.info("-" * 80)

        for _, row in transactions_df.iterrows():
            # Check that all required fields exist
            if not all(field in row for field in ['date', 'description', 'amount']):
                logger.warning(f"Skipping transaction due to missing required fields: {row}")
                continue
                
            # Create transaction object using standardized column names
            transaction = {
                "amount": self._format_amount(row.get('amount', 0)),
                "title": row.get('clean_description', row.get('description', '')),
                "notes": row.get('notes', ''),
                "date": self._format_date(row.get('date', '')),
                "category": row.get('category', ''),
                "account": row.get('account', '')
            }
            
            # Remove empty values to keep the URL clean
            transaction = {k: v for k, v in transaction.items() if v}
            
            transactions_data.append(transaction)
            
            # Log the transaction
            amount = float(transaction['amount'])
            logger.info(f"{transaction['date']:<12} {amount:>10.2f} {transaction.get('category', 'Uncategorized'):<20} {transaction['title']}")

        logger.info("=" * 80)
        
        # Convert to JSON and encode for URL
        transactions_json = json.dumps({"transactions": transactions_data})
        encoded_data = urllib.parse.quote(transactions_json)
        
        # Create app link
        app_link = f"{self.base_url}/addTransaction?JSON={encoded_data}"
        
        logger.info(f"Created app link with {len(transactions_data)} transactions")
        return app_link
    
    def create_app_links(self, transactions_df, batch_size=50):
        """
        Create multiple Cashew app links by splitting transactions into batches
        
        Args:
            transactions_df (DataFrame): DataFrame with processed transactions
            batch_size (int): Number of transactions per batch (default: 50)
            
        Returns:
            list: List of Cashew app links
        """
        app_links = []
        total_transactions = len(transactions_df)
        
        for i in range(0, total_transactions, batch_size):
            batch_df = transactions_df.iloc[i:i+batch_size]
            app_link = self.create_app_link(batch_df)
            if app_link:
                app_links.append(app_link)
        
        logger.info(f"Created {len(app_links)} app links with {total_transactions} total transactions")
        return app_links
    
    def send_email(self, app_links, subject="Your Cashew App Links"):
        """
        Send app links via email
        
        Args:
            app_links (list): List of Cashew app links
            subject (str): Email subject
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            if not self.email_settings:
                logger.error("Cannot send email: No email settings loaded")
                return False
            
            recipient_email = self.email_settings.get('recipient')
            logger.info(f"Starting email sending process to {recipient_email}")
            
            # Check if app links are valid
            if not app_links:
                logger.error("Cannot send email: No valid app links")
                return False
                
            # Get SMTP settings from configuration
            smtp_config = self.email_settings.get('smtp', {})
            smtp_server = smtp_config.get('server')
            smtp_port = smtp_config.get('port')
            smtp_user = smtp_config.get('user')
            smtp_password = smtp_config.get('password')
            sender_email = self.email_settings.get('sender')
            
            logger.info(f"SMTP Configuration - Server: {smtp_server}, Port: {smtp_port}, User: {smtp_user}, Sender: {sender_email}")
            
            if not all([smtp_server, smtp_port, smtp_user, smtp_password, sender_email, recipient_email]):
                missing_configs = [k for k, v in {'smtp.server': smtp_server, 'smtp.port': smtp_port, 
                                                'smtp.user': smtp_user, 'smtp.password': '***', 
                                                'sender': sender_email, 'recipient': recipient_email}.items() if not v]
                logger.error(f"Cannot send email: Missing SMTP configuration - {', '.join(missing_configs)}")
                return False
            
            # Create email
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Date'] = datetime.now()
            
            # Email content
            email_content = f"""
            Hello,
            
            Here are your Cashew app links:
            
            """
            
            # Add each app link on a new line
            for i, app_link in enumerate(app_links, 1):
                email_content += f"<a href=\"{app_link}\">Link{i}</a><br>\n"
            
            email_content += """
            Click the links to view your transactions in the Cashew app.
            """
            
            msg.set_content(email_content)
            msg.add_alternative(email_content, subtype='html')
            logger.info("Email message created successfully")
            
            # Send email
            logger.info(f"Attempting to connect to SMTP server {smtp_server}:{smtp_port}")
            if int(smtp_port) == 465:
                logger.info("Using SMTP_SSL for secure connection")
                try:
                    with smtplib.SMTP_SSL(smtp_server, int(smtp_port), timeout=30) as server:
                        logger.info("Connected to SMTP server, attempting to login")
                        server.login(smtp_user, smtp_password)
                        logger.info("Login successful, sending message")
                        server.send_message(msg)
                        logger.info("Message sent successfully")
                except socket.timeout:
                    logger.error("Connection to SMTP server timed out")
                    return False
                except ssl.SSLError as e:
                    logger.error(f"SSL error occurred: {str(e)}")
                    return False
                except ConnectionRefusedError:
                    logger.error("Connection to SMTP server was refused")
                    return False
            else:
                with smtplib.SMTP(smtp_server, int(smtp_port), timeout=30) as server:
                    logger.info("Connected to SMTP server, starting TLS")
                    server.starttls()
                    logger.info("TLS started, attempting to login")
                    server.login(smtp_user, smtp_password)
                    logger.info("Login successful, sending message")
                    server.send_message(msg)
                    logger.info("Message sent successfully")
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False 