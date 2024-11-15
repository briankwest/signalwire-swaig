from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from urllib.parse import urlsplit, urlunsplit
from typing import Dict, Any, Callable, Optional, List, Union
from dataclasses import dataclass
import logging
import os
import json
log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.DEBUG))

@dataclass
class SWAIGArgumentItems:
    type: str
    enum: Optional[List[str]] = None

@dataclass
class SWAIGArgument:
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None
    items: Optional[SWAIGArgumentItems] = None

class SWAIG:
    def __init__(self, app: Flask, auth: Optional[tuple[str, str]] = None):
        logging.debug("Initializing SWAIG with app: %s and auth: %s", app, auth)
        self.app = app
        self.auth = HTTPBasicAuth() if auth else None
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.auth_creds = auth
        self.function_objects: Dict[str, Callable] = {}
        
        logging.debug("SWAIG initialized with functions: %s", self.functions)
        
        self._setup_routes()

    def _build_argument_items(self, param: Union[SWAIGArgumentItems]) -> Dict[str, Any]:
        schema = {"type": param.type}
        if param.enum:
            schema["enum"] = param.enum
        return schema
    
    def endpoint(self, description: str, **params: SWAIGArgument):
        def decorator(func: Callable):
            logging.debug("Registering endpoint: %s with description: %s and params: %s", func.__name__, description, params)
            self.functions[func.__name__] = {
                "description": description,
                "function": func.__name__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        name: {key: value for key, value in {
                            "type": param.type,
                            "description": param.description,
                            "default": param.default,
                            "enum": param.enum,
                            "items": self._build_argument_items(param.items) if param.items else None
                        }.items() if value is not None}
                        for name, param in params.items()
                    },
                    "required": [
                        name for name, param in params.items()
                        if param.required
                    ]
                }
            }
            self.function_objects[func.__name__] = func
            logging.debug("Endpoint registered: %s", func.__name__)
            return func
        return decorator

    def _setup_routes(self):
        logging.debug("Setting up routes")
        def route_handler():
            logging.debug("Handling request at /swaig endpoint")
            data = request.json
            
            if data.get('action') == "get_signature":
                logging.debug("Action is get_signature")
                return self._handle_signature_request(data)

            logging.debug("Action is function call")
            return self._handle_function_call(data)

        if self.auth:
            logging.debug("Applying authentication to route handler")
            route_handler = self.auth.verify_password(route_handler)
        
        self.app.route('/swaig', methods=['POST'])(route_handler)
        logging.debug("Routes setup complete")
    
    def _handle_signature_request(self, data):
        logging.debug("Handling signature request with data: %s", data)
        requested = data.get("functions") or list(self.functions.keys())
        base_url = self._get_base_url()

        signatures = []
        for name in requested:
            if name in self.functions:
                func_info = self.functions[name].copy()
                func_info["web_hook_url"] = f"{base_url}/swaig"
                signatures.append(func_info)
        logging.debug("Signature request handled, returning signatures: %s", signatures)
        return jsonify(signatures)
    
    def _handle_function_call(self, data):
        logging.debug("Handling function call with data: %s", data)
        function_name = data.get('function')
        if not function_name:
            logging.error("Function name not provided")
            return jsonify({"response": "Function name not provided"}), 200

        func = self.function_objects.get(function_name)
        if not func:
            logging.error("Function not found: %s", function_name)
            return jsonify({"response": "Function not found"}), 200

        params = data.get('argument', {}).get('parsed', [{}])[0]

        meta_data = data.get('meta_data', {})
        logging.debug("meta_data type: %s", type(meta_data).__name__)
        if isinstance(meta_data, dict):
            logging.debug("meta_data is a valid dictionary: %s", meta_data)
        else:
            logging.error("meta_data is not a valid dictionary: %s", meta_data)
            return jsonify({"response": "meta_data is not a valid dictionary"}), 200
        

        meta_data_token = data.get('meta_data_token', None)
        logging.debug("meta_data_token type: %s", type(meta_data_token).__name__)
        if not isinstance(meta_data_token, str):
            logging.error("meta_data_token is not a valid string: %s", meta_data_token)
            return jsonify({"response": "meta_data_token is not a valid string"}), 200

        
        # Ensure that params is a dictionary
        logging.debug("params type: %s", type(params).__name__)
        if not isinstance(params, dict):
            logging.error("Parameters are not a dictionary: %s", params)
            return jsonify({"response": "Invalid parameters format"}), 200

        logging.debug("Calling function: %s with params: %s, meta_data_token: %s, meta_data: %s", function_name, params, meta_data_token, meta_data)

        try:
            response, meta_data = func(**params, meta_data_token=meta_data_token, **meta_data)
            logging.debug("Function %s executed successfully with response: %s, meta_data: %s", function_name, response, meta_data)
            if meta_data:
                return jsonify({"response": response, "action": [{"set_meta_data": meta_data}]})
            else:
                return jsonify({"response": response})
        except TypeError as e:
            logging.error("TypeError executing function %s: %s", function_name, str(e))
            return jsonify({"response": f"Invalid arguments for function '{function_name}': {str(e)}"}), 200
        except Exception as e:
            logging.error("Error executing function %s: %s", function_name, str(e))
            return jsonify({"response": str(e)}), 200


    def _get_base_url(self):
        logging.debug("Getting base URL")
        url = urlsplit(request.host_url.rstrip('/'))
        
        if self.auth_creds:
            username, password = self.auth_creds
            netloc = f"{username}:{password}@{url.netloc}"
        else:
            netloc = url.netloc
            
        if url.scheme != 'https':
            url = url._replace(scheme='https')
            
        logging.debug("Base URL obtained: %s", urlunsplit((url.scheme, netloc, url.path, url.query, url.fragment)))
        return urlunsplit((url.scheme, netloc, url.path, url.query, url.fragment)) 