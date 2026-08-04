import time
import hashlib
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class DDoSProtectionMiddleware:
    """
    Middleware to protect against DDoS attacks using rate limiting
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Configuration (requests per time window)
        self.RATE_LIMIT = getattr(settings, 'DDOS_RATE_LIMIT', 100)  
        self.TIME_WINDOW = getattr(settings, 'DDOS_TIME_WINDOW', 60)  
        self.BLOCK_DURATION = getattr(settings, 'DDOS_BLOCK_DURATION', 300)  
        
        # Stricter limits for authentication endpoints
        self.AUTH_RATE_LIMIT = getattr(settings, 'DDOS_AUTH_RATE_LIMIT', 5)
        self.AUTH_TIME_WINDOW = getattr(settings, 'DDOS_AUTH_TIME_WINDOW', 60)
        
        # WebSocket rate limits
        self.WS_RATE_LIMIT = getattr(settings, 'DDOS_WS_RATE_LIMIT', 50)
        self.WS_TIME_WINDOW = getattr(settings, 'DDOS_WS_TIME_WINDOW', 60)

    def __call__(self, request):
        # Get client identifier (IP address)
        client_ip = self.get_client_ip(request)
        
        # Check if IP is blocked
        if self.is_blocked(client_ip):
            logger.warning(f"Blocked request from {client_ip} - IP is temporarily blocked")
            return HttpResponseForbidden("Too many requests. Please try again later.")
        
        # Check rate limit based on endpoint type
        if self.is_auth_endpoint(request.path):
            if not self.check_rate_limit(client_ip, 'auth', self.AUTH_RATE_LIMIT, self.AUTH_TIME_WINDOW):
                self.block_ip(client_ip)
                logger.warning(f"Rate limit exceeded for auth endpoint from {client_ip}")
                return JsonResponse({
                    'error': 'Too many authentication attempts. Please try again later.'
                }, status=429)
        else:
            if not self.check_rate_limit(client_ip, 'general', self.RATE_LIMIT, self.TIME_WINDOW):
                self.block_ip(client_ip)
                logger.warning(f"Rate limit exceeded from {client_ip}")
                return HttpResponseForbidden("Rate limit exceeded. Please slow down.")
        
        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """
        Get the client's IP address from the request
        Handles proxy headers
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def check_rate_limit(self, client_ip, limit_type, max_requests, time_window):
        """
        Check if the client has exceeded the rate limit
        Returns True if within limits, False if exceeded
        """
        cache_key = f'rate_limit:{limit_type}:{client_ip}'
        
        # Get current request count and timestamp
        data = cache.get(cache_key, {'count': 0, 'start_time': time.time()})
        
        current_time = time.time()
        time_passed = current_time - data['start_time']
        
        # Reset if time window has passed
        if time_passed > time_window:
            data = {'count': 1, 'start_time': current_time}
            cache.set(cache_key, data, time_window)
            return True
        
        # Increment counter
        data['count'] += 1
        
        # Check if limit exceeded
        if data['count'] > max_requests:
            cache.set(cache_key, data, time_window)
            return False
        
        cache.set(cache_key, data, time_window)
        return True

    def is_blocked(self, client_ip):
        """
        Check if an IP is currently blocked
        """
        block_key = f'blocked_ip:{client_ip}'
        return cache.get(block_key, False)

    def block_ip(self, client_ip):
        """
        Block an IP address for a specified duration
        """
        block_key = f'blocked_ip:{client_ip}'
        cache.set(block_key, True, self.BLOCK_DURATION)
        logger.error(f"IP {client_ip} has been blocked for {self.BLOCK_DURATION} seconds")

    def is_auth_endpoint(self, path):
        """
        Check if the request is to an authentication endpoint
        """
        auth_paths = ['/login/', '/register/', '/logout/']
        return any(path.startswith(auth_path) for auth_path in auth_paths)


class ConnectionThrottleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.MAX_CONNECTIONS = getattr(settings, 'MAX_CONNECTIONS_PER_IP', 10)
        self.TTL = getattr(settings, 'CONNECTION_TTL', 5)  # shorter TTL

    def __call__(self, request):
        client_ip = self.get_client_ip(request)
        key = f'active_connections:{client_ip}'

        # Initialize key if not exists
        cache.add(key, 0, self.TTL)

        try:
            current_connections = cache.incr(key)
        except ValueError:
            # If the key doesn't exist for some reason
            cache.set(key, 1, self.TTL)
            current_connections = 1

        if current_connections > self.MAX_CONNECTIONS:
            # Decrement back immediately to free slot
            cache.decr(key)
            return HttpResponseForbidden("Too many concurrent connections")

        try:
            response = self.get_response(request)
        finally:
            try:
                cache.decr(key)
            except ValueError:
                cache.set(key, 0, self.TTL)

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class RequestSizeMiddleware:
    """
    Middleware to limit request payload size to prevent memory exhaustion attacks
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Maximum request body size in bytes (default 10MB)
        self.MAX_BODY_SIZE = getattr(settings, 'MAX_REQUEST_BODY_SIZE', 10 * 1024 * 1024)

    def __call__(self, request):
        # Check content length
        content_length = request.META.get('CONTENT_LENGTH')
        
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > self.MAX_BODY_SIZE:
                    logger.warning(f"Request body too large: {content_length} bytes")
                    return HttpResponseForbidden("Request body too large")
            except ValueError:
                pass
        
        response = self.get_response(request)
        return response