#!/usr/bin/env python3
"""
API Data Fetcher
Fetches data from a REST API and stores it in a SQLite database.
Created by ProfessorXAI
"""

import requests
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APIDataFetcher:
    """A class to fetch data from APIs and store in SQLite database."""
    
    def __init__(self, db_path: str = "api_data.db"):
        """
        Initialize the API Data Fetcher.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database
    
    def _init_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor
        
        # Create table for storing API responses
        cursor.execute('
            CREATE TABLE IF NOT EXISTS api_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                request_url TEXT NOT NULL,
                response_data TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                headers TEXT
            )
        ')
        
        # Create table for storing parsed data items
        cursor.execute('
            CREATE TABLE IF NOT EXISTS data_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER,
                item_key TEXT,
                item_value TEXT,
                item_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (response_id) REFERENCES api_responses(id)
            )
        ')
        
        # Create index for faster queries
        cursor.execute('
            CREATE INDEX IF NOT EXISTS idx_endpoint ON api_responses(endpoint)
        ')
        
        self.conn.commit
        logger.info(f"Database initialized at {self.db_path}")
    
    def fetch_data(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch data from an API endpoint.
        
        Args:
            url: The API endpoint URL
            method: HTTP method (GET, POST, etc.)
            headers: Optional request headers
            params: Optional query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary containing response data or None if failed
        """
        try:
            logger.info(f"Fetching data from: {url}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=timeout
            )
            
            response.raise_for_status
            
            data = response.json
            
            # Store in database
            self._store_response(
                endpoint=url.split('/')[-1] or 'root',
                request_url=url,
                response_data=data,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
            logger.info(f"Successfully fetched and stored data from {url}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
    
    def _store_response(
        self,
        endpoint: str,
        request_url: str,
        response_data: Any,
        status_code: int,
        headers: Dict[str, str]
    ) -> int:
        """
        Store API response in the database.
        
        Returns:
            The ID of the inserted record
        """
        cursor = self.conn.cursor
        
        cursor.execute('
            INSERT INTO api_responses (endpoint, request_url, response_data, status_code, headers)
            VALUES (?, ?, ?, ?, ?)
        ', (
            endpoint,
            request_url,
            json.dumps(response_data),
            status_code,
            json.dumps(headers)
        ))
        
        response_id = cursor.lastrowid
        
        # Parse and store individual data items if response is a list or dict
        self._parse_and_store_items(response_id, response_data)
        
        self.conn.commit
        return response_id
    
    def _parse_and_store_items(
        self,
        response_id: int,
        data: Any,
        prefix: str = ""
    ) -> None:
        """Recursively parse and store data items."""
        cursor = self.conn.cursor
        
        if isinstance(data, dict):
            for key, value in data.items:
                item_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    self._parse_and_store_items(response_id, value, item_key)
                else:
                    cursor.execute('
                        INSERT INTO data_items (response_id, item_key, item_value, item_type)
                        VALUES (?, ?, ?, ?)
                    ', (response_id, item_key, str(value), type(value).__name__))
                    
        elif isinstance(data, list):
            for i, item in enumerate(data):
                item_key = f"{prefix}[{i}]" if prefix else f"[{i}]"
                if isinstance(item, (dict, list)):
                    self._parse_and_store_items(response_id, item, item_key)
                else:
                    cursor.execute('
                        INSERT INTO data_items (response_id, item_key, item_value, item_type)
                        VALUES (?, ?, ?, ?)
                    ', (response_id, item_key, str(item), type(item).__name__))
    
    def get_stored_responses(
        self,
        endpoint: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve stored API responses from the database.
        
        Args:
            endpoint: Filter by endpoint name (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of stored responses
        """
        cursor = self.conn.cursor
        
        if endpoint:
            cursor.execute('
                SELECT * FROM api_responses
                WHERE endpoint = ?
                ORDER BY fetched_at DESC
                LIMIT ?
            ', (endpoint, limit))
        else:
            cursor.execute('
                SELECT * FROM api_responses
                ORDER BY fetched_at DESC
                LIMIT ?
            ', (limit,))
        
        rows = cursor.fetchall
        return [dict(row) for row in rows]
    
    def search_data_items(
        self,
        search_key: str
    ) -> List[Dict[str, Any]]:
        """
        Search for specific data items by key pattern.
        
        Args:
            search_key: Key pattern to search for (supports SQL LIKE wildcards)
            
        Returns:
            List of matching data items
        """
        cursor = self.conn.cursor
        
        cursor.execute('
            SELECT di.*, ar.endpoint, ar.request_url
            FROM data_items di
            JOIN api_responses ar ON di.response_id = ar.id
            WHERE di.item_key LIKE ?
            ORDER BY di.created_at DESC
        ', (f"%{search_key}%",))
        
        rows = cursor.fetchall
        return [dict(row) for row in rows]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor
        
        cursor.execute('SELECT COUNT(*) as count FROM api_responses')
        total_responses = cursor.fetchone['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM data_items')
        total_items = cursor.fetchone['count']
        
        cursor.execute('
            SELECT endpoint, COUNT(*) as count
            FROM api_responses
            GROUP BY endpoint
            ORDER BY count DESC
        ')
        endpoints = [dict(row) for row in cursor.fetchall]
        
        return {
            'total_responses': total_responses,
            'total_data_items': total_items,
            'endpoints': endpoints
        }
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close
            logger.info("Database connection closed")


def main:
    """Example usage of the API Data Fetcher."""
    # Initialize the fetcher
    fetcher = APIDataFetcher("api_data.db")
    
    try:
        # Example: Fetch data from JSONPlaceholder API (a free fake API for testing)
        print("\n=== Fetching Posts ===")
        posts = fetcher.fetch_data("https://jsonplaceholder.typicode.com/posts?_limit=5")
        if posts:
            print(f"Fetched {len(posts)} posts")
        
        print("\n=== Fetching Users ===")
        users = fetcher.fetch_data("https://jsonplaceholder.typicode.com/users?_limit=3")
        if users:
            print(f"Fetched {len(users)} users")
        
        print("\n=== Fetching Comments ===")
        comments = fetcher.fetch_data("https://jsonplaceholder.typicode.com/comments?_limit=5")
        if comments:
            print(f"Fetched {len(comments)} comments")
        
        # Display statistics
        print("\n=== Database Statistics ===")
        stats = fetcher.get_statistics
        print(f"Total API responses stored: {stats['total_responses']}")
        print(f"Total data items parsed: {stats['total_data_items']}")
        print("\nEndpoints:")
        for ep in stats['endpoints']:
            print(f"  - {ep['endpoint']}: {ep['count']} requests")
        
        # Search for specific data
        print("\n=== Searching for 'email' fields ===")
        email_items = fetcher.search_data_items("email")
        for item in email_items[:5]:
            print(f"  {item['item_key']}: {item['item_value']}")
        
        # Get stored responses
        print("\n=== Recent Stored Responses ===")
        responses = fetcher.get_stored_responses(limit=5)
        for resp in responses:
            print(f"  [{resp['status_code']}] {resp['endpoint']} - {resp['fetched_at']}")
            
    finally:
        fetcher.close


if __name__ == "__main__":
    main
