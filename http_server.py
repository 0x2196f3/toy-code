from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import mimetypes

class StaticServer(BaseHTTPRequestHandler):
    def do_GET(self):
        # Serve the index.html file if the root is requested
        if self.path == '/':
            self.path = '/index.html'
        
        # Construct the file path
        file_path = os.path.join(os.getcwd(), self.path.lstrip('/'))

        # Check if the requested file exists
        if os.path.exists(file_path):
            # Guess the MIME type of the file
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'  # Default to binary type if unknown
            
            # Send the response
            self.send_response(200)
            self.send_header('Content-type', mime_type)
            self.end_headers()
            with open(file_path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            # If the file does not exist, send a 404 response
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'File not found')

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, StaticServer)
    print('Server running at http://localhost:8000/')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
