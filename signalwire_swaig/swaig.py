from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from urllib.parse import urlsplit, urlunsplit
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
import logging
import os
from .response import SWAIGResponse

log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.DEBUG))

@dataclass
class SWAIGArgumentItems:
    type: str
    enum: Optional[List[str]] = None
    properties: Optional[Dict[str, 'SWAIGArgument']] = None
    required: Optional[List[str]] = None
    items: Optional['SWAIGArgumentItems'] = None

@dataclass
class SWAIGArgument:
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None
    items: Optional[SWAIGArgumentItems] = None

@dataclass
class SWAIGFunctionProperties:
    active: Optional[bool] = None
    wait_file: Optional[str] = None
    wait_file_loops: Optional[int | str] = None
    wait_for_fillers: Optional[bool] = None
    fillers: Optional[Dict[str, List[str]]] = None

def build_schema(param):
    """Recursively build a JSON schema from SWAIGArgument or SWAIGArgumentItems."""
    schema = {"type": param.type}
    if getattr(param, "description", None):
        schema["description"] = param.description
    if getattr(param, "enum", None):
        schema["enum"] = param.enum
    if getattr(param, "default", None) is not None:
        schema["default"] = param.default
    if param.type == "object" and getattr(param, "properties", None):
        schema["properties"] = {k: build_schema(v) for k, v in param.properties.items()}
        if getattr(param, "required", None):
            schema["required"] = param.required
    if param.type == "array" and getattr(param, "items", None):
        schema["items"] = build_schema(param.items)
    return schema

def remove_none(d):
    """Recursively remove keys with None values from dictionaries and lists."""
    if isinstance(d, dict):
        return {k: remove_none(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        return [remove_none(v) for v in d if v is not None]
    else:
        return d

def error_response(message):
    """Helper to return a JSON error response."""
    swaigresp = SWAIGResponse(message)
    return jsonify(swaigresp.to_dict()), 200

class SWAIG:
    def __init__(self, app: Flask = None, auth: Optional[tuple[str, str]] = None):
        self.app = None
        self.auth = HTTPBasicAuth() if auth else None
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.auth_creds = auth
        self.function_objects: Dict[str, Callable] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        self.app = app
        self._setup_routes()

    def endpoint(self, description: str, function_properties: Optional[SWAIGFunctionProperties] = None, **params: SWAIGArgument):
        def decorator(func: Callable):
            func_meta = {
                "description": description,
                "function": func.__name__,
            }
            if function_properties:
                func_meta.update(function_properties.__dict__)
            func_meta["parameters"] = {
                "type": "object",
                "properties": {name: build_schema(param) for name, param in params.items()},
                "required": [name for name, param in params.items() if param.required]
            }
            self.functions[func.__name__] = func_meta
            self.function_objects[func.__name__] = func

            def wrapper(*args, **kwargs):
                meta_data = request.json.get('meta_data', {})
                meta_data_token = request.json.get('meta_data_token', None)
                if not isinstance(meta_data, dict):
                    return error_response("Invalid meta_data format. It should be a dictionary.")
                if meta_data_token is not None and not isinstance(meta_data_token, str):
                    return error_response("Invalid meta_data_token format. It should be a string.")
                return func(*args, meta_data=meta_data, meta_data_token=meta_data_token, **kwargs)
            logging.debug(f"Registering endpoint: {func.__name__}")
            return wrapper
        return decorator

    def _setup_routes(self):
        if not self.app:
            raise RuntimeError("App not set for SWAIG")
        def route_handler():
            logging.debug("Handling request at /swaig endpoint")
            data = request.json
            logging.debug(f"Request data: {data}")
            if data.get('action') == "get_signature":
                logging.debug("Action is get_signature")
                return self._handle_signature_request(data)
            logging.debug("Action is function call")
            return self._handle_function_call(data)
        if self.auth:
            route_handler = self.auth.verify_password(route_handler)
        self.app.route('/swaig', methods=['POST'])(route_handler)

    def _handle_signature_request(self, data):
        logging.debug(f"Handling signature request with data: {data}")
        requested = data.get("functions") or list(self.functions.keys())
        logging.debug(f"Requested function signatures: {requested}")
        base_url = self._get_base_url()
        signatures = []
        for name in requested:
            if name in self.functions:
                func_info = self.functions[name].copy()
                func_info["web_hook_url"] = f"{base_url}/swaig"
                signatures.append(remove_none(func_info))
        logging.debug(f"Signature request handled, returning signatures: {signatures}")
        return jsonify(signatures)

    def _handle_function_call(self, data):
        logging.debug(f"Handling function call with data: {data}")
        function_name = data.get('function')
        if not function_name:
            logging.error("Function name not provided")
            return error_response("Function name not provided")
        func = self.function_objects.get(function_name)
        if not func:
            logging.error(f"Function not found: {function_name}")
            return error_response("Function not found")
        params = data.get('argument', {}).get('parsed', [{}])[0]
        meta_data = data.get('meta_data', {}).copy()
        meta_data['call_id'] = data.get('call_id', None)
        meta_data_token = data.get('meta_data_token', None)
        logging.debug(f"Calling function: {function_name} with params: {params}, meta_data: {meta_data}, meta_data_token: {meta_data_token}")
        if not isinstance(meta_data, dict):
            return error_response("meta_data is not a valid dictionary")
        if meta_data_token is not None and not isinstance(meta_data_token, str):
            return error_response("meta_data_token is not a valid string")
        if not isinstance(params, dict):
            return error_response("Invalid parameters format")
        try:
            function_params = params.copy()
            result = func(meta_data=meta_data, meta_data_token=meta_data_token, **function_params)
            logging.debug(f"Function {function_name} returned: {result}")
            
            # Check if the result is already a SWAIGResponse
            if isinstance(result, SWAIGResponse):
                return jsonify(result.to_dict())
            
            # Handle existing return formats (backward compatibility)
            if isinstance(result, tuple):
                if len(result) == 1:
                    response, actions = result[0], None
                elif len(result) == 2:
                    response, actions = result
                else:
                    return error_response(f"Function '{function_name}' did not return a tuple of one or two elements")
            else:
                response, actions = result, None
                
            # Create response dictionary (legacy format)
            if actions:
                return jsonify({"response": response, "action": actions})
            else:
                return jsonify({"response": response})
                
        except TypeError as e:
            return error_response(f"Invalid arguments for function '{function_name}': {str(e)}")
        except Exception as e:
            return error_response(str(e))

    def _get_base_url(self):
        url = urlsplit(request.host_url.rstrip('/'))
        if self.auth_creds:
            username, password = self.auth_creds
            netloc = f"{username}:{password}@{url.netloc}"
        else:
            netloc = url.netloc
        if url.scheme != 'https':
            url = url._replace(scheme='https')
        return urlunsplit((url.scheme, netloc, url.path, url.query, url.fragment)) 