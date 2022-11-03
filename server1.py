from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>HELLO</title></head>", "utf-8"))
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes("<p>This the example web server 1.</p>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))


def main():
    httpd = HTTPServer(("0.0.0.0", 80), SimpleHTTPRequestHandler)
    httpd.serve_forever()



if __name__ == "__main__":
    main()

