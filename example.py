from pyplugin import register, generate_ai_plugin_and_openapi_spec, launch_server
from fastapi import FastAPI


app = FastAPI()

@register(app, methods=["GET", "POST"])
async def hello(name: str, age: int = 5) -> str:
    """ Greets user """
    return f"Hello, {name}! Age {age}."

@register(app, methods=["GET"])
async def add(a: int, b: int) -> int:
    """ Adds numbers """
    return a + b

if __name__ == "__main__":
    # Generate the necessary files
    generate_ai_plugin_and_openapi_spec(app)

    # Launch the server
    launch_server(app)

