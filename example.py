from src.autoplugin.autoplugin import register, generate_files, launch_server
from fastapi import FastAPI
from testing import testing_server
from os.path import join


app = FastAPI()


@register(app, methods=["GET", "POST"], generate_description=True)
async def hello(name: str, age: int = 5) -> str:
    return f"Hello, {name}! Age {age}."


@register(app, methods=["GET"], generate_description=True)
async def add(a: int, b: int) -> int:
    return a + b


def test_hello():
    # Generate the necessary files
    generate_files(app)

    # Launch and test the server
    host = "127.0.0.1"
    port = 8000
    server, base_url = testing_server(host=host, port=port, app_file=__file__, app_var="app")

    with server.run_in_thread():
        # Server is started. Do your tests here.       
        
        url = join(base_url, "hello")

        import requests
        
        response = requests.post(url, json={"name": "John Doe"})
        assert response.json() == {"result": "Hello, John Doe! Age 5."}

        response = requests.get(url, params={"name": "Jane Doe", "age": 10})
        assert response.json() == {"result": "Hello, Jane Doe! Age 10."}
        # Server will be stopped.


if __name__ == "__main__":
    # Generate the necessary files
    generate_files(app, out_dir=".well-known")

    # Test /hello endpoint
    test_hello()

    # Launch the server
    launch_server(app)
        