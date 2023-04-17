"""
Copyright (c) 2023, Suvansh Sanjeev
All rights reserved.

This source code is licensed under the BSD-style license found in the
LICENSE file in the root directory of this source tree. 
"""
import functools
import os
from os.path import join
import inspect
from typing import Callable, List, Dict, Any, Optional
from fastapi import FastAPI, Depends
import uvicorn
from pydantic import BaseModel, create_model
from fastapi.openapi.utils import get_openapi
import yaml
import json


_func_description_chain = None


def launch(app: FastAPI, host="127.0.0.1", port=8000):
    uvicorn.run(app, host=host, port=port)


def generate(app: FastAPI, out_dir=".well-known", **kwargs):
    """ kwargs should be key-value pairs for the plugin_spec json """
    os.makedirs(out_dir, exist_ok=True)
    openapi = get_openapi(
        title="Custom ChatGPT Plugin",
        version="1.0.0",
        routes=app.routes,
    )

    with open(join(out_dir, "openapi.yaml"), "w") as openapi_yaml:
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
    _plugin_check_limit(plugin_spec, "name_for_human", 50)
    _plugin_check_limit(plugin_spec, "name_for_model", 50)
    _plugin_check_limit(plugin_spec, "description_for_human", 120)
    _plugin_check_limit(plugin_spec, "description_for_model",
                       8000)  # will decrease over time

    with open(join(out_dir, "ai-plugin.json"), "w") as plugin_json:
        json.dump(plugin_spec, plugin_json, indent=4)


def register(app: FastAPI,
             func: Callable = None,
             *,
             methods: List[str] = None,
             description: Optional[str] = None,
             generate_description: Optional[bool] = None,
             ) -> Callable:
    if func is None:
        return functools.partial(register, app, methods=methods, description=description, generate_description=generate_description)

    if description is None:
        if generate_description is None:
            # user did not specify whether to generate. generate if no docstring, otherwise use docstring
            description = _generate_description(func) if func.__doc__ is None else func.__doc__
        elif generate_description:
            description = _generate_description(func)
        else:  # generate_description is False. use docstring if it exists, otherwise use None (no description)
            description = func.__doc__
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


def _plugin_check_limit(plugin_spec: Dict[str, Any], key: str, char_limit: int):
    assert len(plugin_spec[key]) <= char_limit, \
        f"Key \"{key}\" in plugin spec is too long. Expected: <={char_limit}, found: {len(plugin_spec[key])}."


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
            raise ImportError("Please install LangChain to generate function descriptions. Otherwise, set `generate_description=False` when registering your function.")
        llm = OpenAI(temperature=0, max_tokens=100)
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