import sys
import time
import socket
import threading
import webview
from app import create_app

def find_free_port(start_port=5000):
    """Find an available TCP port for the local Flask backend server."""
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
            port += 1
    return 5000

def run_flask(app, host, port):
    """Run Flask server in background thread without debug reloaders."""
    from werkzeug.serving import run_simple
    run_simple(host, port, app, threaded=True, use_reloader=False)

def main():
    app = create_app()
    host = '127.0.0.1'
    port = find_free_port(5000)
    server_url = f'http://{host}:{port}'

    # Start Flask server thread
    server_thread = threading.Thread(
        target=run_flask,
        args=(app, host, port),
        daemon=True
    )
    server_thread.start()

    # Wait until local server responds
    retries = 30
    ready = False
    while retries > 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) == 0:
                ready = True
                break
        time.sleep(0.1)
        retries -= 1

    if not ready:
        print(f"Warning: Flask backend on {server_url} took longer than expected to bind.")

    # Create native desktop window using pywebview
    window = webview.create_window(
        title="ClinicFlow — Clinical Practice Management System",
        url=server_url,
        width=1280,
        height=850,
        min_size=(960, 640),
        text_select=True,
        zoomable=True
    )

    # Start pywebview event loop
    webview.start(debug=False)

if __name__ == '__main__':
    main()
