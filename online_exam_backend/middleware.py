from urllib.parse import urlunsplit
from django.http import HttpResponseRedirect


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
