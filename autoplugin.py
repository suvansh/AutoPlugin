import functools
import os
import inspect
from typing import Callable, List, Dict, Any, Optional
from fastapi import FastAPI, Depends
import uvicorn
from pydantic import BaseModel, create_model
from fastapi.openapi.utils import get_openapi
import yaml
import json


_func_description_chain = None


def register(app: FastAPI,
             func: Callable = None,
             *,
             methods: List[str] = None,
             description: Optional[str] = None,
             generate_description: bool = True,
             ) -> Callable:
    if func is None:
        return functools.partial(register, app, methods=methods, description=description, generate_description=generate_description)

    if description is None and generate_description:
        print("Generating description for function", func.__name__)
        description = _generate_description(func)
    if methods is None:
        methods = ["POST"]

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

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

            app.get(f"/{func.__name__}", description=description)(get_wrapper)
        elif method == "POST":
            post_wrapper = get_post_wrapper(func)
            app.post(f"/{func.__name__}",
                     description=description)(post_wrapper)

    return wrapper


def plugin_check_limit(plugin_spec: Dict[str, Any], key: str, char_limit: int):
    assert len(plugin_spec[key]) <= char_limit, \
        f"Key \"{key}\" in plugin spec is too long. Expected: <={char_limit}, found: {len(plugin_spec[key])}."


def generate_files(app: FastAPI, **kwargs):
    """ kwargs should be key-value pairs for the plugin_spec json """
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
    plugin_check_limit(plugin_spec, "description_for_model",
                       8000)  # will decrease over time

    with open("output/ai-plugin.json", "w") as plugin_json:
        json.dump(plugin_spec, plugin_json, indent=4)


def launch_server(app: FastAPI, host="127.0.0.1", port=8000):
    uvicorn.run(app, host=host, port=port)


def _generate_description(func: Callable) -> str:
    def _get_langchain_description(func_str: str) -> str:
        global _func_description_chain
        if _func_description_chain is not None:
            return _func_description_chain.run(func_str=func_str)
        try:
            from langchain.llms import OpenAI
            from langchain.prompts import PromptTemplate
            from langchain.chains import LLMChain
        except ImportError:
            raise ImportError("Please install langchain to generate function descriptions.")
        llm = OpenAI(temperature=0.9)
        # prompt = PromptTemplate(
        #     input_variables=["func_str"],
        #     template="""
        #         Come up with a concise description for this function for the OpenAPI spec that would serve as a useful description for a ChatGPT plugin to know when to call it.
        #         It should be at most one or two sentences, and must be less than 50 words.
        #         Function:
        #         ```python
        #         {func_str}
        #         ```
        #         Description:
        #         """
        # )
        prompt = PromptTemplate(
            input_variables=["func_str"],
            template="""
                Come up with a concise description for this function for the OpenAPI spec that would serve as a useful description for a ChatGPT plugin to know when to call it.
                It should be at most one or two sentences, and must be less than 50 words.
                Function:
                ```python
                async def add(a: int, b: int) -> int:
                    return a + b
                ```
                Description:
                Adds two numbers
                Function:
                ```python
                async def hello(name: str) -> str:
                    return "Hello, " + name + "!".
                ```
                Description:
                Greets person with specified name.
                Function:
                ```python
                async def pow(base: int, power: int = 2) -> int:
                    return base ** pow
                ```
                Description:
                Raises a number to a power.
                Function:
                ```python
                {func_str}
                ```
                Description:
                """
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        _func_description_chain = chain
        return chain.run(func_str=func_str)

    try:
        func_str = inspect.getsource(func)
    except (OSError, TypeError):
        signature = inspect.signature(func)
        params = []
        for param in signature.parameters.values():
            if param.annotation == inspect.Parameter.empty:
                params.append(param.name)
            else:
                params.append(f"{param.name}: {param.annotation.__name__}")
        return_description = "" if signature.return_annotation == inspect.Signature.empty else f" -> {signature.return_annotation.__name__}"
        signature_string = f"{func.__name__}({', '.join(params)}){return_description}"
        func_doc = f"\n\t{func.__doc__}" if func.__doc__ is not None else ""
        func_str = f"{signature_string}{func_doc}"
    description = _get_langchain_description(func_str)
    return description