import socket
import threading
import webbrowser

from app import create_app


def available_port():
    for port in range(5001, 5011):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No open port from 5001 to 5010")


def main():
    port = available_port()
    url = f"http://127.0.0.1:{port}/"
    print(f"Library demo: {url}", flush=True)
    print("Keep this window open while presenting. Press Ctrl+C to stop.", flush=True)
    threading.Timer(2, lambda: webbrowser.open(url)).start()
    create_app().run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
