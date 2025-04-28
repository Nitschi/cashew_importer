# Cashew Importer

A Python application that imports bank transaction CSVs, processes them, and exports them as Cashew app links.

## Features

- Parse CSV files from bank statements to extract account information and transactions
- Clean transaction descriptions using regex to remove bloat
- Categorize transactions using a two-step approach:
  1. First try keyword matching for faster, rule-based categorization
  2. Fall back to OpenAI for transactions that couldn't be matched by keywords
- Generate Cashew app links with categorized transactions
- Send app links via email or save to file

## Setup

1. Copy the example configuration files from `example_config/` to `config/`:
   ```bash
   cp example_config/* config/
   ```

2. Adjust the configuration files in the `config/` based on the `example_config` directory to match your setup:
   - `accounts.json`: Define your bank accounts with names and account numbers
   - `email.json`: Configure SMTP settings for email notifications
   - `ai_classifier_settings.json`: Set up OpenAI API key and category hints
   - `keyword_rules.json`: Define keyword-based categorization rules
   - `my_categories.json`: Define your custom transaction categories

## Usage with Docker

1. Build and run the container:
   ```bash
   docker-compose up --build
   ```

2. The application will:
   - Mount the `input/` directory for CSV files
   - Mount the `output/` directory for generated app links
   - Mount all configuration files from the `config/` directory

3. Place your bank statement CSV files in the `input/` directory, and the application will process them automatically.

4. Optional: Enable verbose logging by uncommenting the `command: --verbose` line in `docker-compose.yml`

## Configuration Files

### accounts.json
Define your bank accounts with the following structure:
```json
{
    "accounts": [
        {
            "name": "Account Name",
            "number": "Account Number",
            "weight": 1.0
        }
    ]
}
```

### email.json
Configure email settings:
```json
{
    "smtp": {
        "server": "your.smtp.server",
        "port": 465,
        "user": "your@email.com",
        "password": "your-password"
    },
    "sender": "your@email.com",
    "recipient": "recipient@email.com"
}
```

### ai_classifier_settings.json
Configure OpenAI settings and category hints:
```json
{
    "openai": {
        "api_key": "your-openai-api-key",
        "model": "gpt-4.1-mini"
    },
    "category_hints": {
        "Category": "Hint for categorization"
    }
}
``` 
