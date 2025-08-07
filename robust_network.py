"""
Robust Network Operations with Integrated Error Handling and Retry Logic.

Enhances network operations with intelligent retry strategies, connection pooling,
and comprehensive error handling.
"""

import requests
import time
import random
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from error_logging_integration import robust_operation, get_integrated_logger, OperationContext
from error_handling import ErrorCategory, ErrorSeverity, NetworkError, ErrorInfo
from logging_config import get_logger

logger = get_logger()


@dataclass
class NetworkConfig:
    """Configuration for network operations."""
    max_retries: int = 3
    backoff_factor: float = 1.0
    timeout: tuple = (10, 30)  # (connect_timeout, read_timeout)
    retry_on_status: tuple = (500, 502, 503, 504, 520, 521, 522, 523, 524)
    max_retry_delay: float = 120.0
    jitter: bool = True


class RobustSession:
    """
    Enhanced requests session with intelligent retry and error handling.
    """
    
    def __init__(self, config: Optional[NetworkConfig] = None):
        self.config = config or NetworkConfig()
        self.integrated_logger = get_integrated_logger()
        self.session = self._create_session()
        self._request_count = 0
        self._error_count = 0
        
    def _create_session(self) -> requests.Session:
        """Create a configured requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=self.config.retry_on_status,
            backoff_factor=self.config.backoff_factor,
            raise_on_status=False
        )
        
        # Add adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    @robust_operation(
        operation_name="http_request",
        component="network",
        max_retries=3,
        retry_delay=2.0
    )
    def request(
        self,
        method: str,
        url: str,
        description: str = "",
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with robust error handling and monitoring.
        """
        self._request_count += 1
        request_id = f"req_{self._request_count}_{int(time.time())}"
        
        context = OperationContext(
            operation_name=f"http_{method.lower()}",
            component="network",
            request_id=request_id,
            metadata={
                'method': method,
                'url': url,
                'description': description,
                'timeout': self.config.timeout
            }
        )
        
        with self.integrated_logger.operation_context(context):
            try:
                # Set default timeout if not provided
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = self.config.timeout
                
                start_time = time.time()
                response = self.session.request(method, url, **kwargs)
                duration = time.time() - start_time
                
                # Log request details
                logger.debug(
                    f"HTTP {method} {url} -> {response.status_code} ({duration:.2f}s)",
                    extra={
                        'component': 'network',
                        'method': method,
                        'url': url,
                        'status_code': response.status_code,
                        'duration': duration,
                        'request_id': request_id,
                        'response_size': len(response.content) if response.content else 0
                    }
                )
                
                # Handle HTTP errors
                if response.status_code >= 400:
                    error_info = ErrorInfo(
                        category=ErrorCategory.NETWORK,
                        severity=self._determine_http_error_severity(response.status_code),
                        message=f"HTTP {response.status_code} error for {method} {url}",
                        details={
                            'status_code': response.status_code,
                            'response_text': response.text[:500] if response.text else None,
                            'url': url,
                            'method': method,
                            'request_id': request_id
                        }
                    )
                    
                    self._error_count += 1
                    
                    if response.status_code >= 500:
                        # Server errors - potentially retryable
                        raise NetworkError(error_info)
                    elif response.status_code in [401, 403]:
                        # Authentication errors - usually not retryable
                        error_info.severity = ErrorSeverity.HIGH
                        error_info.recoverable = False
                        raise NetworkError(error_info)
                    elif response.status_code == 404:
                        # Not found - usually not retryable but not critical
                        error_info.severity = ErrorSeverity.MEDIUM
                        error_info.recoverable = False
                        raise NetworkError(error_info)
                    else:
                        # Other client errors
                        error_info.severity = ErrorSeverity.MEDIUM
                        raise NetworkError(error_info)
                
                return response
                
            except requests.exceptions.RequestException as e:
                self._error_count += 1
                
                # Classify request exceptions
                if isinstance(e, requests.exceptions.Timeout):
                    severity = ErrorSeverity.MEDIUM
                    message = f"Request timeout for {method} {url}"
                elif isinstance(e, requests.exceptions.ConnectionError):
                    severity = ErrorSeverity.HIGH
                    message = f"Connection error for {method} {url}"
                else:
                    severity = ErrorSeverity.MEDIUM
                    message = f"Request error for {method} {url}: {str(e)}"
                
                error_info = ErrorInfo(
                    category=ErrorCategory.NETWORK,
                    severity=severity,
                    message=message,
                    details={
                        'exception_type': type(e).__name__,
                        'url': url,
                        'method': method,
                        'request_id': request_id,
                        'error_count': self._error_count
                    }
                )
                
                raise NetworkError(error_info, original_exception=e)
    
    def _determine_http_error_severity(self, status_code: int) -> ErrorSeverity:
        """Determine error severity based on HTTP status code."""
        if status_code >= 500:
            return ErrorSeverity.HIGH
        elif status_code in [401, 403]:
            return ErrorSeverity.HIGH
        elif status_code == 404:
            return ErrorSeverity.MEDIUM
        elif status_code == 429:  # Rate limiting
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def get(self, url: str, description: str = "", **kwargs) -> requests.Response:
        """Make GET request with error handling."""
        return self.request("GET", url, description, **kwargs)
    
    def post(self, url: str, description: str = "", **kwargs) -> requests.Response:
        """Make POST request with error handling."""
        return self.request("POST", url, description, **kwargs)
    
    def put(self, url: str, description: str = "", **kwargs) -> requests.Response:
        """Make PUT request with error handling."""
        return self.request("PUT", url, description, **kwargs)
    
    def delete(self, url: str, description: str = "", **kwargs) -> requests.Response:
        """Make DELETE request with error handling."""
        return self.request("DELETE", url, description, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            'total_requests': self._request_count,
            'total_errors': self._error_count,
            'error_rate': self._error_count / max(self._request_count, 1),
            'session_id': id(self.session)
        }


class ConnectionManager:
    """
    Enhanced connection manager with session pooling and health monitoring.
    """
    
    def __init__(self, max_sessions: int = 5):
        self.max_sessions = max_sessions
        self.sessions: Dict[str, RobustSession] = {}
        self.session_health: Dict[str, Dict[str, Any]] = {}
        self.integrated_logger = get_integrated_logger()
        
    def get_session(self, session_id: str = "default") -> RobustSession:
        """
        Get or create a robust session.
        """
        if session_id not in self.sessions:
            if len(self.sessions) >= self.max_sessions:
                # Remove least recently used session
                oldest_session = min(
                    self.session_health.items(),
                    key=lambda x: x[1].get('last_used', 0)
                )[0]
                
                logger.info(
                    f"Removing old session {oldest_session} to make room",
                    extra={
                        'component': 'network',
                        'action': 'session_cleanup',
                        'removed_session': oldest_session,
                        'session_count': len(self.sessions)
                    }
                )
                
                del self.sessions[oldest_session]
                del self.session_health[oldest_session]
            
            # Create new session
            self.sessions[session_id] = RobustSession()
            self.session_health[session_id] = {
                'created_at': time.time(),
                'last_used': time.time(),
                'request_count': 0,
                'error_count': 0
            }
            
            logger.debug(
                f"Created new session: {session_id}",
                extra={
                    'component': 'network',
                    'action': 'session_created',
                    'session_id': session_id
                }
            )
        
        # Update last used time
        self.session_health[session_id]['last_used'] = time.time()
        
        return self.sessions[session_id]
    
    def close_session(self, session_id: str):
        """Close and remove a session."""
        if session_id in self.sessions:
            self.sessions[session_id].session.close()
            del self.sessions[session_id]
            del self.session_health[session_id]
            
            logger.debug(
                f"Closed session: {session_id}",
                extra={
                    'component': 'network',
                    'action': 'session_closed',
                    'session_id': session_id
                }
            )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get connection manager health status."""
        total_requests = sum(
            health.get('request_count', 0) 
            for health in self.session_health.values()
        )
        total_errors = sum(
            health.get('error_count', 0) 
            for health in self.session_health.values()
        )
        
        return {
            'active_sessions': len(self.sessions),
            'max_sessions': self.max_sessions,
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate': total_errors / max(total_requests, 1),
            'session_details': self.session_health.copy()
        }


def smart_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    Calculate smart delay with exponential backoff and jitter.
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    if jitter:
        # Add random jitter (±25%)
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(delay, 0.1)  # Minimum delay of 0.1 seconds


# Global connection manager
_connection_manager = ConnectionManager()

def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return _connection_manager

def get_robust_session(session_id: str = "default") -> RobustSession:
    """Get a robust session from the global connection manager."""
    return _connection_manager.get_session(session_id)
