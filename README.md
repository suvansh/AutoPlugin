# AutoPlugin

AutoPlugin is a Python package that makes it easy to convert Python functions into [ChatGPT plugins](https://openai.com/blog/chatgpt-plugins). With just a couple lines of code, you can:
- Automatically create an OpenAPI spec with custom endpoints for your registered Python functions, telling ChatGPT how to use it. Pull endpoint descriptions from the function docstring or generate them automatically with the OpenAI API.
- Generate the `ai-plugin.json` file to register your plugin with ChatGPT.
- Launch a local server that can be used by ChatGPT for development.

## Installation

To install AutoPlugin, simply run the following command:

```bash
pip install autoplugin
```

To install with the ability to generate endpoint descriptions for the OpenAPI specification automatically from source code, install with

```bash
pip install autoplugin[gen]
```

## Basic Usage
To get started with AutoPlugin, follow these steps:

1. Import the necessary functions from AutoPlugin and FastAPI:
```python
from autoplugin.autoplugin import register, generate, launch
from fastapi import FastAPI
```

2. Create a FastAPI app instance:
```python
app = FastAPI()
```

3. Use the register decorator to register your functions as API endpoints.
AutoPlugin generates function descriptions in the OpenAPI spec so that ChatGPT knows how to use your endpoints.
By default, the description is fetched from the docstring. If there's no docstring, or if you specify `generate_description=True`, AutoPlugin will generate one automatically from OpenAI's API (requires setting the `OPENAI_API_KEY` environment variable).
Finally, you can specify a description (e.g. if the docstring contains extra information not needed in the OpenAPI description) by passing the `description` keyword argument:
```python
@register(app, methods=["GET", "POST"], generate_description=True)
async def hello(name: str, age: int = 5) -> str:
    return f"Hello, {name}! Age {age}."
```

4. Generate the necessary files (`openapi.yaml` and `ai-plugin.json`) for your ChatGPT plugin.
Optionally, specify `out_dir` to change where they're saved to:
```python
generate(app)  # generated files saved to `.well-known/` directory
```

5. Launch the server. Optionally, specify `host` and `port`:
```python
launch(app)  # API hosted at localhost:8000
```


## Example

Here's a complete example that demonstrates how to use AutoPlugin to create API endpoints for two functions, `hello` and `add`.
It also generates the `openapi.yaml` and `ai-plugin.json` files, by default in the `.well-known` directory. :
```python
from autoplugin.autoplugin import register, generate, launch
from fastapi import FastAPI

app = FastAPI()

@register(app, methods=["GET", "POST"])
async def hello(name: str, age: int = 5) -> str:
    return f"Hello, {name}! Age {age}."

@register(app, methods=["GET"])
async def add(a: int, b: int) -> int:
    """ Adds two numbers """
    return a + b


# Generate the necessary files
generate(app)

# Launch the server
launch(app)
```

This example creates a FastAPI server with two endpoints, `/hello` and `/add`, that can be accessed using GET or POST requests.
AutoPlugin will use the docstring for the OpenAPI description of `/add` and generate an automatic description for `/hello` by passing the source code of the function to OpenAI's API.


## Testing
AutoPlugin also provides a `testing_server` utility (courtesy of [florimondmanca](https://github.com/encode/uvicorn/issues/742#issuecomment-674411676)) for testing your endpoints. Here's an example of how you can use it to test the `/hello` and `/add` endpoints from the example above:
```python
from autoplugin.testing import testing_server
from os.path import join
import requests

def test_api():
    host = "127.0.0.1"
    port = 8000
    server, base_url = testing_server(host=host, port=port, app_file="path/to/example.py", app_var="app")

    with server.run_in_thread():
        # Server is started. Do your tests here.
        response = requests.post(join(base_url, "hello"), json={"name": "John Doe", "age": 31})
        assert response.json() == {"result": "Hello, John Doe! Age 31."}

        response = requests.get(join(base_url, "hello"), params={"name": "Jane Smith"})
        assert response.json() == {"result": "Hello, Jane Smith! Age 5."}

        response = requests.get(join(base_url, "add"), params={"a": 6, "b": 8})
        assert response.json() == {"result": 14}
        # Server will be stopped.

test_api()
```

