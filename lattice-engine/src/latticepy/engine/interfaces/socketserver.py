import os
import sys
import json
import socketserver

from LatticePy.interfaces.clientinterface import VectorDBlist, Promptlist, LatticeTools, LLMmodels, LlmConnections
from LatticePy.interfaces.agentinterface import LatticeAgent

SOCKET_PATH = "/tmp/latticeai.sock"

class LatticeAIRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            data = self.rfile.readline().decode().strip()
            if not data:
                return
            request = json.loads(data)
            cmd = request.get("cmd")
            if cmd == "list_prompts":
                result = list(Promptlist.listdown())
            elif cmd == "list_agents":
                result = list(LatticeAgent.listdown())
            elif cmd == "list_tools":
                result = list(LatticeTools.listdown())
            elif cmd == "list_connections":
                result = list(LlmConnections.listdown())
            elif cmd == "list_models":
                result = list(LLMmodels().listdown())
            else:
                result = {"error": "Unknown command"}
            self.wfile.write((json.dumps(result) + "\n").encode())
        except Exception as e:
            self.wfile.write((json.dumps({"error": str(e)}) + "\n").encode())

def run_socket_server():
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)
    with socketserver.UnixStreamServer(SOCKET_PATH, LatticeAIRequestHandler) as server:
        print(f"LatticeAI Unix socket server running at {SOCKET_PATH}")
        server.serve_forever()

if __name__ == "__main__":
    if sys.platform != "linux":
        print("Unix domain sockets are only supported on Linux.")
        sys.exit(1)
    run_socket_server()