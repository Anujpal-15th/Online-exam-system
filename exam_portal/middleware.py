from urllib.parse import urlunsplit
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import logout


class BlockedUserMiddleware:
    """  
    Middleware to check if a user is blocked and prevent them from accessing the system.
    Blocked users will be logged out and shown a message.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip check for certain paths
        excluded_paths = [
            '/auth/login/',
            '/auth/logout/',
            '/auth/register/',
            '/static/',
            '/media/',
        ]
        
        if request.user.is_authenticated and not any(request.path.startswith(path) for path in excluded_paths):
            if hasattr(request.user, 'is_blocked') and request.user.is_blocked:
                logout(request)
                return render(request, 'accounts/blocked_user.html', status=403)

        response = self.get_response(request)
        return response


class LocalhostRedirectMiddleware:
    """
    In development, ensure a single origin by redirecting 127.0.0.1 -> localhost.

    Why: Browsers treat http://127.0.0.1:8000 and http://localhost:8000 as different
    origins, so cookies/sessions differ and you can see different output.

    Behavior:
    - For safe methods (GET/HEAD/OPTIONS), if the request host is 127.0.0.1,
      issue a 302 redirect to the same URL on localhost, preserving scheme, port,
      path, and query string.
    - For other methods (e.g., POST), do not redirect to avoid losing request body.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        hostname = host.split(":", 1)[0]

        if hostname == "127.0.0.1" and request.method in ("GET", "HEAD", "OPTIONS"):
            scheme = "https" if request.is_secure() else "http"
            port = request.get_port()

            netloc = "localhost"
            if port and port not in ("80", "443"): 
                netloc = f"{netloc}:{port}"

            redirect_url = urlunsplit(
                (scheme, netloc, request.path, request.META.get("QUERY_STRING", ""), "")
            )
            return HttpResponseRedirect(redirect_url)

        return self.get_response(request)
