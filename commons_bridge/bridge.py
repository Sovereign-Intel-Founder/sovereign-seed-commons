import socketserver

class SafeParticipantHandler(socketserver.BaseRequestHandler):
    """TCP request handler for safe participant integration testing."""
    def handle(self):
        try:
            data = self.request.recv(1024)
            if data:
                self.request.sendall(data)
        except Exception:
            pass
