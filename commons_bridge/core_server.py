import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from commons_bridge.adapters.json_rpc_adapter import LocalloopbackJsonRpcAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("core_server")

class CoreJsonRpcHandler(BaseHTTPRequestHandler):
    adapter = LocalloopbackJsonRpcAdapter({"host": "127.0.0.1"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        # Run the async handle_request method synchronously in the handler context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.adapter.initialize())
            response_dict = loop.run_until_complete(self.adapter.handle_request(body))
            response_body = json.dumps(response_dict).encode('utf-8')
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as e:
            error_res = json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None}).encode('utf-8')
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_res)
        finally:
            loop.close()

    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

def run():
    host = "127.0.0.1"
    port = 9900
    server_address = (host, port)
    httpd = HTTPServer(server_address, CoreJsonRpcHandler)
    logger.info(f"Sovereign Core Communication Layer running on {host}:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
