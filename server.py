from http.server import HTTPServer
from api.index import handler


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 3000), handler).serve_forever()
