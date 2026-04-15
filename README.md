# API Data Fetcher

A Python script that fetches data from REST APIs and stores it in a SQLite database.

## Features

- 🔄 Fetch data from any REST API endpoint
- 💾 Automatic storage in SQLite database
- 📊 Parses and indexes nested JSON data
- 🔍 Search functionality for stored data
- 📈 Database statistics and reporting
- 📝 Comprehensive logging

## Installation

```bash
# Clone the repository
git clone https://github.com/sir-william/api-data-fetcher.git
cd api-data-fetcher

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from api_fetcher import APIDataFetcher

# Initialize the fetcher
fetcher = APIDataFetcher("my_data.db")

# Fetch data from an API
data = fetcher.fetch_data("https://api.example.com/data")

# Close connection when done
fetcher.close
```

### Advanced Usage

```python
from api_fetcher import APIDataFetcher

fetcher = APIDataFetcher("api_data.db")

# Fetch with custom headers and parameters
data = fetcher.fetch_data(
    url="https://api.example.com/users",
    method="GET",
    headers={"Authorization": "Bearer token123"},
    params={"limit": 10, "offset": 0},
    timeout=60
)

# Get statistics
stats = fetcher.get_statistics
print(f"Total responses: {stats['total_responses']}")

# Search for specific data
results = fetcher.search_data_items("email")
for item in results:
    print(f"{item['item_key']}: {item['item_value']}")

# Get stored responses
responses = fetcher.get_stored_responses(endpoint="users", limit=10)

fetcher.close
```

### Run the Demo

```bash
python api_fetcher.py
```

This will fetch sample data from JSONPlaceholder API and demonstrate all features.

## Database Schema

### api_responses
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| endpoint | TEXT | API endpoint name |
| request_url | TEXT | Full request URL |
| response_data | TEXT | JSON response data |
| status_code | INTEGER | HTTP status code |
| fetched_at | TIMESTAMP | When data was fetched |
| headers | TEXT | Response headers (JSON) |

### data_items
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| response_id | INTEGER | Foreign key to api_responses |
| item_key | TEXT | Nested key path |
| item_value | TEXT | Value as string |
| item_type | TEXT | Python type name |
| created_at | TIMESTAMP | When item was parsed |

## License

MIT License

## Created By

ProfessorXAI Team
