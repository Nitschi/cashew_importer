#!/usr/bin/env python3
import os
import argparse
import logging
import glob
import shutil
from datetime import datetime
from src.csv_importer import get_importer
from src.transaction_processor import TransactionProcessor
from src.app_link_exporter import AppLinkExporter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_arguments():
    """
    Parse command line arguments
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Cashew Importer - Import banking transactions and generate Cashew app links')
    
    parser.add_argument('--categories', '-c', default='config/my_categories.json', help='Path to the categories JSON file')
    parser.add_argument('--keywords', '-k', default='config/keyword_rules.json', help='Path to the keyword rules JSON file for categorization')
    parser.add_argument('--ai-settings', '-a', default='config/ai_classifier_settings.json', help='Path to the AI classifier settings JSON file')
    parser.add_argument('--accounts', '-ac', default='config/accounts.json', help='Path to the accounts JSON file')
    parser.add_argument('--email', '-e', default='config/email.json', help='Email address to send the app links to')
    parser.add_argument('--input', '-i', default='input', help='Path to the input directory')
    parser.add_argument('--output', '-o', default='output/app_link.txt', help='Path to save the app link to (if not sending via email)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    return parser.parse_args()

def archive_file(file_path: str) -> None:
    """
    Move a file to the archive directory with a timestamp
    
    Args:
        file_path (str): Path to the file to archive
    """
    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    new_filename = f"{name}_{timestamp}{ext}"
    archive_path = os.path.join('input/archive', new_filename)
    
    shutil.move(file_path, archive_path)
    logger.info(f"Archived {filename} to {archive_path}")

def main():
    # Parse arguments
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Find all CSV files in the input directory
    csv_files = glob.glob(f'{args.input}/*.csv')
    if not csv_files:
        logger.warning(f"No CSV files found in the input directory: {args.input}")
        return
    
    for csv_file in csv_files:
        logger.info(f"Processing file: {csv_file}")
        
        # 1. Import CSV
        importer = get_importer(csv_file, args.accounts)
        transactions_df = importer.import_csv()
        
        # 2. Process transactions
        logger.info("Processing transactions")
        processor = TransactionProcessor(args.categories, args.keywords, args.ai_settings)
        processed_df = processor.process_transactions(transactions_df)
        
        # 3. Create app link
        logger.info("Creating app links")
        exporter = AppLinkExporter(email_settings_file=args.email)
        app_links = exporter.create_app_links(processed_df)
        
        if not app_links:
            logger.error(f"Failed to create app links for {csv_file}")
            continue
        
        # 4. Send email or save to file
        if args.email:
            logger.info("Sending app links via email")
            success = exporter.send_email(
                app_links,
                subject=f"Cashew App Links - {os.path.basename(csv_file)}"
            )
            if not success:
                logger.error("Failed to send email")
                continue
        elif args.output:
            output_file = f"{os.path.splitext(args.output)[0]}_{os.path.basename(csv_file)}"
            logger.info(f"Saving app links to {output_file}")
            with open(output_file, 'w') as f:
                for i, app_link in enumerate(app_links, 1):
                    f.write(f"Link{i}: {app_link}\n\n")
        else:
            # Print to console
            print(f"\nCashew App Links for {csv_file}:")
            for i, app_link in enumerate(app_links, 1):
                print(f"Link{i}: {app_link}\n")
        
        # Archive the processed file
        archive_file(csv_file)
    
    logger.info("Done processing all files!")

if __name__ == "__main__":
    main() 