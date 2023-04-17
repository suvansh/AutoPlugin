from autoplugin import register, generate, launch
from fastapi import FastAPI
from autoplugin.testing import testing_server
from os.path import join


app = FastAPI()


@register(app, methods=["GET", "POST"])
async def hello(name: str, age: int = 5) -> str:
    return f"Hello, {name}! Age {age}."


@register(app, methods=["GET"])
async def add(a: int, b: int) -> int:
    """ Add two numbers together. """
    return a + b


def test_api():
    import requests

    host = "127.0.0.1"
    port = 8000
    server, base_url = testing_server(host=host, port=port, app_file=__file__, app_var="app")

    with server.run_in_thread():
        # Server is started. Do your tests here.
        response = requests.post(join(base_url, "hello"), json={"name": "John Doe", "age": 31})
        assert response.json() == {"result": "Hello, John Doe! Age 31."}

        response = requests.get(join(base_url, "hello"), params={"name": "Jane Smith"})
        assert response.json() == {"result": "Hello, Jane Smith! Age 5."}

        response = requests.get(join(base_url, "add"), params={"a": 6, "b": 8})
        assert response.json() == {"result": 14}
        # Server will be stopped.


if __name__ == "__main__":
    # Generate the necessary files
    generate(app, name="example", description="Adds numbers and greets users.")

    # Test endpoints
    test_api()

    # Launch the server
    launch(app)
        