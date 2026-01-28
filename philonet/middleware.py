import logging
import time


logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path not in {'/accounts/login/', '/signup/'}:
            return self.get_response(request)
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info("Timing %s %s %.1fms", request.method, request.path, duration_ms)
        return response
