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
pip install 'autoplugin[gen]'
```

## Basic Usage
To get started with AutoPlugin, follow these steps:

1. Import the necessary functions from AutoPlugin:
```python
from autoplugin import register, generate, launch, get_app
```

2. Create an app instance, backed by FastAPI:
```python
app = get_app()
```

3. Use the register decorator to register your functions as API endpoints.
AutoPlugin will automatically generate descriptions if needed.
```python
@register(app, methods=["GET"])
async def get_order(name: str) -> str:
    order = await get_order_from_db(name)
    return f"Order for {name}: {order}"
# Generated description: "Retrieves an order from the database for a given name."
```

4. Generate the necessary files (`openapi.yaml` and `ai-plugin.json`) for your ChatGPT plugin.
Optionally, specify `out_dir` to change where they're saved to,
or set `overwrite_openapi_spec=False` or `overwrite_plugin_spec=False` to avoid overwriting the respective files.
```python
# generated files saved to `.well-known/` directory
generate(app, name="Example", description="Plugin to add numbers or greet users")
```

5. Launch the server. Optionally, specify `host` and `port`:
```python
launch(app)  # API hosted at localhost:8000
```

6. Follow the [instructions](https://platform.openai.com/docs/plugins/getting-started/running-a-plugin) to run a custom plugin:
- On ChatGPT, make a new chat.
- Under "Models" select "Plugins"
- In the Plugins dropdown, select "Plugin store"
- Click "Develop your own plugin"
- Enter the URL you're running the server at ("localhost:8000" by default) and hit enter.
- Click "Install localhost plugin" 


## Example

Here's a complete example that demonstrates how to use AutoPlugin to create API endpoints for two functions, `hello` and `add`.
It also generates the `openapi.yaml` and `ai-plugin.json` files, by default in the `.well-known` directory. :
```python
from autoplugin.autoplugin import register, generate, launch, get_app

app = get_app()

@register(app, methods=["GET", "POST"])
async def hello(name: str, age: int = 5) -> str:
    return f"Hello, {name}! Age {age}."

@register(app, methods=["GET"])
async def add(a: int, b: int) -> int:
    """ Adds two numbers """
    return a + b


# Generate the necessary files
generate(app, name="Example", description="Plugin to add numbers or greet users")

# Launch the server
launch(app)
```

This example creates a FastAPI server with two endpoints, `/hello` and `/add`, that can be accessed using GET or POST requests.
AutoPlugin will use the docstring for the OpenAPI description of `/add` and generate an automatic description for `/hello` by passing the source code of the function to OpenAI's API.


## Docs 

### The `@register` Decorator

The `@register` decorator is used as follows:

```python
@register(app: FastAPI,
            methods: List[str],                     # which HTTP methods to support
            description: Optional[str],             # if provided, used as is
            generate_description: Optional[bool])   # whether to autogenerate a description
def my_func(...):
    ...
```

AutoPlugin generates function descriptions in the OpenAPI spec so that ChatGPT knows how to use your endpoints. There are a few arguments to customize the behavior of this generation.

- `app`: Your FastAPI application. AutoPlugin provides a `get_app` function that includes CORSMiddleware for testing convenience (allows all origins by default).
- `methods`: A list of HTTP methods to be supported (e.g. ”GET”, POST”)
- `description`: If provided, overrides everything else and is used directly as the endpoint description for the OpenAPI spec
- `generate_description`: If set to `True`, AutoPlugin will generate one automatically from OpenAI's API (requires the LangChain package and setting the `OPENAI_API_KEY` environment variable).

By default (if neither `description` nor `generate_description` are provided), the description is fetched from the docstring. If there's no docstring, AutoPlugin falls back to generating one automatically.


### The `generate` Function

The `generate` function has the following signature:

```python
def generate(app: FastAPI, version="v1", out_dir=".well-known",
             overwrite_plugin_spec=True, overwrite_openapi_spec=True,
             name="", description="",
             **kwargs)
```

- `app`: Your FastAPI application again.
- `version="v1"`: What version number to pass to both the plugin and OpenAPI specs.
- `out_dir=".well-known"`: The directory to save both files to.
- `overwrite_plugin_spec=True`: If set to False, does not overwrite `ai-plugin.json` if it already exists.
- `overwrite_openapi_spec=True`: If set to False, does not overwrite `openapi.yaml` if it already exists.
- `name=""`: If specified, used for both `name_for_human` and `name_for_model`.
- `description=""`: If specified, used for both `description_for_human` and `description_for_model`. Keep in mind the [best practices](https://platform.openai.com/docs/plugins/getting-started/writing-descriptions) for descriptions.
- `**kwargs`: All other keyword arguments are passed on to `ai-plugin.json` directly. See the full list of possible options [here](https://platform.openai.com/docs/plugins/getting-started/plugin-manifest).


### The `launch` Function

The `launch` function has the following signature:

```python
def launch(app: FastAPI, host="127.0.0.1", port=8000):
```

- `app`: Still your FastAPI application.
- `host="127.0.0.1"`: the host to launch the server on
- `port=8000`: the port to launch the server on


### Testing
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

