import asyncio
import sqlite3
import time
import json
import hashlib
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class GitHubHost:
    """Represents a GitHub host/repository."""
    id: Optional[int] = None
    owner: str = ""
    repo: str = ""
    full_name: str = ""
    description: str = ""
    url: str = ""
    clone_url: str = ""
    ssh_url: str = ""
    language: str = ""
    stars: int = 0
    forks: int = 0
    created_at: str = ""
    updated_at: str = ""
    pushed_at: str = ""
    cached_at: str = ""

    def __post_init__(self):
        if not self.full_name and self.owner and self.repo:
            self.full_name = f"{self.owner}/{self.repo}"


@dataclass
class GitHubAPIOptions:
    """Configuration options for GitHub API requests."""
    max_pages: Optional[int] = None
    per_page: int = 100
    timeout: int = 30
    retry_attempts: int = 3
    base_delay: float = 1.0
    cache_duration_hours: int = 24


class GitHubDatabase:
    """SQLite database manager for GitHub data."""

    def __init__(self, db_path: str = "github_cache.db"):
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self) -> None:
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS github_hosts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner TEXT NOT NULL,
                    repo TEXT NOT NULL,
                    full_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    url TEXT,
                    clone_url TEXT,
                    ssh_url TEXT,
                    language TEXT,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    pushed_at TEXT,
                    cached_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint_hash TEXT UNIQUE NOT NULL,
                    endpoint TEXT NOT NULL,
                    params_json TEXT,
                    response_json TEXT NOT NULL,
                    cached_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hosts_full_name 
                ON github_hosts(full_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hosts_language 
                ON github_hosts(language)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_hash 
                ON api_cache(endpoint_hash)
            """)

            conn.commit()

    def save_host(self, host: GitHubHost) -> int:
        """Save or update a GitHub host in the database."""
        host.cached_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO github_hosts 
                (owner, repo, full_name, description, url, clone_url, ssh_url, 
                 language, stars, forks, created_at, updated_at, pushed_at, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                host.owner, host.repo, host.full_name, host.description,
                host.url, host.clone_url, host.ssh_url, host.language,
                host.stars, host.forks, host.created_at, host.updated_at,
                host.pushed_at, host.cached_at
            ))
            return conn.lastrowid

    def get_host(self, full_name: str) -> Optional[GitHubHost]:
        """Retrieve a host by full name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM github_hosts WHERE full_name = ?",
                (full_name,)
            )
            row = cursor.fetchone()
            if row:
                return GitHubHost(**dict(row))
        return None

    def search_hosts(self, query: str, language: str = None) -> List[GitHubHost]:
        """Search hosts by query and optionally filter by language."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT * FROM github_hosts 
                WHERE (full_name LIKE ? OR description LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%"]

            if language:
                sql += " AND language = ?"
                params.append(language)

            sql += " ORDER BY stars DESC LIMIT 100"

            cursor = conn.execute(sql, params)
            return [GitHubHost(**dict(row)) for row in cursor.fetchall()]

    def cache_api_response(self, endpoint: str, params: Dict, response: Any) -> None:
        """Cache an API response."""
        endpoint_hash = hashlib.md5(
            f"{endpoint}{json.dumps(params, sort_keys=True)}".encode()
        ).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO api_cache 
                (endpoint_hash, endpoint, params_json, response_json, cached_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                endpoint_hash, endpoint, json.dumps(params),
                json.dumps(response), datetime.now().isoformat()
            ))

    def get_cached_response(self, endpoint: str, params: Dict,
                            max_age_hours: int = 24) -> Optional[Any]:
        """Get cached API response if not expired."""
        endpoint_hash = hashlib.md5(
            f"{endpoint}{json.dumps(params, sort_keys=True)}".encode()
        ).hexdigest()

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT response_json FROM api_cache 
                WHERE endpoint_hash = ? AND datetime(cached_at) > ?
            """, (endpoint_hash, cutoff_time.isoformat()))

            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def cleanup_old_cache(self, max_age_days: int = 7) -> int:
        """Remove old cache entries."""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM api_cache 
                WHERE datetime(cached_at) < ?
            """, (cutoff_time.isoformat(),))
            return cursor.rowcount


class GitHubRateLimiter:
    """Smart rate limiter that respects GitHub's rate limits."""

    def __init__(self):
        self.last_request_time = 0
        self.remaining_requests = 5000
        self.reset_time = 0
        self.min_delay = 0.1

    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limit info from response headers."""
        if 'x-ratelimit-remaining' in headers:
            self.remaining_requests = int(headers['x-ratelimit-remaining'])
        if 'x-ratelimit-reset' in headers:
            self.reset_time = int(headers['x-ratelimit-reset'])

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        current_time = time.time()

        if self.remaining_requests < 100:
            delay = max(2.0, (self.reset_time - current_time) / max(1, self.remaining_requests))
        else:
            delay = self.min_delay

        time_since_last = current_time - self.last_request_time
        if time_since_last < delay:
            time.sleep(delay - time_since_last)

        self.last_request_time = time.time()


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""

    def __init__(self, message: str, status_code: int, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class GitHubMixin:
    """Modern GitHub API mixin with SQLite caching and improved features."""

    def __init__(self, db_path: str = "github_cache.db"):
        self.rate_limiter = GitHubRateLimiter()
        self.database = GitHubDatabase(db_path)
        self.base_url = 'https://api.github.com'

    def get_github_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        token = self.get_key('github_api')
        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHubMixin/2.0'
        }

    def _parse_link_header(self, link_header: str) -> Dict[str, str]:
        """Parse GitHub's Link header for pagination."""
        links = {}
        for link in link_header.split(','):
            parts = link.strip().split(';')
            if len(parts) == 2:
                url = parts[0].strip('<>')
                rel = parts[1].strip().split('=')[1].strip('"')
                links[rel] = url
        return links

    def _handle_response(self, response) -> Union[Dict, List]:
        """Handle and validate API response."""
        self.rate_limiter.update_from_headers(response.headers)

        if response.status_code == 404:
            return []
        elif response.status_code == 403:
            raise GitHubAPIError(
                "Rate limit exceeded or access forbidden",
                response.status_code,
                response.json() if response.text else {}
            )
        elif response.status_code != 200:
            error_data = response.json() if response.text else {}
            raise GitHubAPIError(
                f"GitHub API error: {error_data.get('message', 'Unknown error')}",
                response.status_code,
                error_data
            )

        return response.json()

    def query_github_api(self, endpoint: str, payload: Dict = None,
                         options: GitHubAPIOptions = None) -> List[Union[Dict, List]]:
        """Query GitHub API with caching and improved error handling."""
        payload = payload or {}
        options = options or GitHubAPIOptions()

        # Check cache first
        cached_response = self.database.get_cached_response(
            endpoint, payload, options.cache_duration_hours
        )
        if cached_response:
            logger.info(f"Using cached response for {endpoint}")
            return cached_response

        headers = self.get_github_headers()
        url = f"{self.base_url}{endpoint}"
        results = []
        page = 1

        while True:
            self.rate_limiter.wait_if_needed()

            current_payload = {**payload, 'page': page, 'per_page': options.per_page}

            try:
                response = self.request('GET', url, headers=headers,
                                        params=current_payload, timeout=options.timeout)
                data = self._handle_response(response)

                if not data:
                    break

                # Handle both list and dict responses
                if isinstance(data, dict):
                    results.append(data)
                else:
                    results.extend(data)

                # Check for pagination
                if ('link' in response.headers and
                        'rel="next"' in response.headers['link'] and
                        (options.max_pages is None or page < options.max_pages)):
                    page += 1
                else:
                    break

            except GitHubAPIError as e:
                logger.error(f"GitHub API error on {endpoint}: {e}")
                if e.status_code == 403:  # Rate limit
                    time.sleep(60)  # Wait a minute and try once more
                    continue
                break
            except Exception as e:
                logger.error(f"Unexpected error querying {endpoint}: {e}")
                break

        # Cache the results
        if results:
            self.database.cache_api_response(endpoint, payload, results)

        return results

    def search_github_repositories(self, query: str, language: str = None,
                                   options: GitHubAPIOptions = None) -> List[GitHubHost]:
        """Search GitHub repositories and save them to database."""
        search_query = query
        if language:
            search_query += f" language:{language}"

        logger.info(f"Searching GitHub repositories for: {search_query}")

        results = self.query_github_api(
            endpoint='/search/repositories',
            payload={'q': search_query, 'sort': 'stars', 'order': 'desc'},
            options=options
        )

        hosts = []
        for result in results:
            if 'items' in result:  # Search results are wrapped
                items = result['items']
            else:
                items = [result] if isinstance(result, dict) else result

            for repo in items:
                host = GitHubHost(
                    owner=repo['owner']['login'],
                    repo=repo['name'],
                    full_name=repo['full_name'],
                    description=repo.get('description', ''),
                    url=repo['html_url'],
                    clone_url=repo['clone_url'],
                    ssh_url=repo['ssh_url'],
                    language=repo.get('language', ''),
                    stars=repo['stargazers_count'],
                    forks=repo['forks_count'],
                    created_at=repo['created_at'],
                    updated_at=repo['updated_at'],
                    pushed_at=repo['pushed_at']
                )

                # Save to database
                self.database.save_host(host)
                hosts.append(host)

        return hosts

    def get_repository_info(self, owner: str, repo: str,
                            force_refresh: bool = False) -> Optional[GitHubHost]:
        """Get detailed repository information."""
        full_name = f"{owner}/{repo}"

        # Check database first unless forcing refresh
        if not force_refresh:
            cached_host = self.database.get_host(full_name)
            if cached_host:
                # Check if cache is still fresh (less than 24 hours old)
                cached_time = datetime.fromisoformat(cached_host.cached_at)
                if datetime.now() - cached_time < timedelta(hours=24):
                    return cached_host

        # Fetch from API
        try:
            results = self.query_github_api(f'/repos/{owner}/{repo}')
            if results:
                repo_data = results[0] if isinstance(results, list) else results

                host = GitHubHost(
                    owner=repo_data['owner']['login'],
                    repo=repo_data['name'],
                    full_name=repo_data['full_name'],
                    description=repo_data.get('description', ''),
                    url=repo_data['html_url'],
                    clone_url=repo_data['clone_url'],
                    ssh_url=repo_data['ssh_url'],
                    language=repo_data.get('language', ''),
                    stars=repo_data['stargazers_count'],
                    forks=repo_data['forks_count'],
                    created_at=repo_data['created_at'],
                    updated_at=repo_data['updated_at'],
                    pushed_at=repo_data['pushed_at']
                )

                self.database.save_host(host)
                return host
        except GitHubAPIError as e:
            logger.error(f"Failed to fetch repository {full_name}: {e}")

        return None

    def search_local_hosts(self, query: str, language: str = None) -> List[GitHubHost]:
        """Search locally cached hosts."""
        return self.database.search_hosts(query, language)

    def cleanup_cache(self, max_age_days: int = 7) -> int:
        """Clean up old cache entries."""
        return self.database.cleanup_old_cache(max_age_days)

    def get_host_statistics(self) -> Dict[str, Any]:
        """Get statistics about cached hosts."""
        with sqlite3.connect(self.database.db_path) as conn:
            stats = {}

            # Total hosts
            cursor = conn.execute("SELECT COUNT(*) FROM github_hosts")
            stats['total_hosts'] = cursor.fetchone()[0]

            # Hosts by language
            cursor = conn.execute("""
                SELECT language, COUNT(*) as count 
                FROM github_hosts 
                WHERE language IS NOT NULL AND language != ''
                GROUP BY language 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_languages'] = dict(cursor.fetchall())

            # Most starred repos
            cursor = conn.execute("""
                SELECT full_name, stars 
                FROM github_hosts 
                ORDER BY stars DESC 
                LIMIT 10
            """)
            stats['most_starred'] = dict(cursor.fetchall())

            return stats


# Example usage and testing
if __name__ == "__main__":
    # This would be used in a larger application that provides the required methods
    class ExampleApp(GitHubMixin):
        def __init__(self):
            super().__init__()

        def get_key(self, key_name: str) -> str:
            # Replace with your actual key management
            return "your_github_token_here"

        def request(self, method: str, url: str, **kwargs):
            # Replace with your actual HTTP client (requests, httpx, etc.)
            import requests
            return requests.request(method, url, **kwargs)

    # Example usage:
    # app = ExampleApp()
    # hosts = app.search_github_repositories("python machine learning", "Python")
    # print(f"Found {len(hosts)} repositories")
    #
    # stats = app.get_host_statistics()
    # print(f"Database statistics: {stats}")