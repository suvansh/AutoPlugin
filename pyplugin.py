import functools
import os
import inspect
from typing import Callable, List, Dict, Any
from fastapi import FastAPI, Depends
import uvicorn
from pydantic import BaseModel, create_model
from fastapi.openapi.utils import get_openapi
import yaml
import json


def register(app: FastAPI, func: Callable = None, *, methods: List[str] = None):
    if func is None:
        return functools.partial(register, app, methods=methods)

    if methods is None:
        methods = ["POST"]

    if not hasattr(app, "registered_functions"):
        app.registered_functions = {}

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    app.registered_functions[func.__name__] = {"func": wrapper, "methods": methods}

    def get_post_wrapper(func):
        signature = inspect.signature(func)
        fields = {
            param.name: (
                param.annotation,
                param.default if param.default != inspect.Parameter.empty else ...,
            )
            for param in signature.parameters.values()
        }
        Model = create_model(func.__name__ + "Model", **fields)

        async def post_wrapper(payload: Model):
            result = await wrapper(**payload.dict())
            return {"result": result}

        return post_wrapper

    for method in methods:
        if method == "GET":
            # Create a Pydantic model for the GET request query parameters
            GetModel = create_model(
                func.__name__ + "GetModel",
                **{
                    param_name: (
                        getattr(inspect.signature(func).parameters[param_name], "annotation", str),
                        (
                            getattr(inspect.signature(func).parameters[param_name], "default", None)
                            if getattr(inspect.signature(func).parameters[param_name], "default", None) != inspect.Parameter.empty
                            else ...
                        ),
                    )
                    for param_name in inspect.signature(func).parameters
                },
            )

            async def get_wrapper(params: GetModel = Depends()):
                result = await wrapper(**params.dict())
                return {"result": result}

            app.get(f"/{func.__name__}", description=func.__doc__)(get_wrapper)
        elif method == "POST":
            post_wrapper = get_post_wrapper(func)
            app.post(f"/{func.__name__}", description=func.__doc__)(post_wrapper)

    return wrapper


def plugin_check_limit(plugin_spec: Dict[str, Any], key: str, char_limit: int):
    assert len(plugin_spec[key]) <= char_limit, f"Key \"{key}\" in plugin spec is too long. Expected: <={char_limit}, found: {len(plugin_spec[key])}."


def generate_ai_plugin_and_openapi_spec(app: FastAPI, **kwargs):
    os.makedirs("output", exist_ok=True)
    openapi = get_openapi(
        title="Custom ChatGPT Plugin",
        version="1.0.0",
        routes=app.routes,
    )

    with open("output/openapi.yaml", "w") as openapi_yaml:
        yaml.dump(openapi, openapi_yaml, sort_keys=False)

    plugin_spec = {
        "name_for_human": "Custom Plugin",
        "name_for_model": "Custom Plugin",
        "description_for_human": "Unspecified custom plugin. Add behavior here.",
        "description_for_model": "Unspecified custom plugin. Add behavior here.",
        "schema_version": "v1",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": "http://localhost:8000/openapi.yaml",
            "is_user_authenticated": False
        },
        "logo_url": "http://example.com/logo.png",
        "contact_email": "support@example.com",
        "legal_info_url": "http://www.example.com/legal"
    }
    plugin_spec.update(kwargs)
    
    # character limit checks
    plugin_check_limit(plugin_spec, "name_for_human", 50)
    plugin_check_limit(plugin_spec, "name_for_model", 50)
    plugin_check_limit(plugin_spec, "description_for_human", 120)
    plugin_check_limit(plugin_spec, "description_for_model", 8000)  # will decrease over time

    with open("output/ai-plugin.json", "w") as plugin_json:
        json.dump(plugin_spec, plugin_json, indent=4)

def launch_server(app: FastAPI, host="127.0.0.1", port=8000):
    uvicorn.run(app, host=host, port=port)

