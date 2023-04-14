# from https://stackoverflow.com/questions/61577643/python-how-to-use-fastapi-and-uvicorn-run-without-blocking-the-thread
import contextlib
import time
import threading
import uvicorn
import requests
from os.path import basename


class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()

def print_response(response):
    if response.status_code == 200:
        resp = f"Response: {response.json()}"
    else:
        resp = f"Error: {response.status_code} - {response.text}"
    print(resp)
    return resp

def testing_server(host="127.0.0.1", port=8000, app_file="example.py", app_var="app"):
    app_base = basename(app_file).split(".")[0]
    config = uvicorn.Config(f"{app_base}:{app_var}", host=host, port=port, log_level="info")
    server = Server(config=config)
    base_url = f"http://{host}:{port}"
    return server, base_url
