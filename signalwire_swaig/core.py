from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from urllib.parse import urlsplit, urlunsplit
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.DEBUG)

@dataclass
class Parameter:
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[list[str]] = None

class SWAIG:
    def __init__(self, app: Flask, auth: Optional[tuple[str, str]] = None):
        logging.debug("Initializing SWAIG with app: %s and auth: %s", app, auth)
        self.app = app
        self.auth = HTTPBasicAuth() if auth else None
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.auth_creds = auth
        self.function_objects: Dict[str, Callable] = {}
        
        self._setup_routes()
    
    def endpoint(self, description: str, **params: Parameter):
        def decorator(func: Callable):
            self.functions[func.__name__] = {
                "description": description,
                "function": func.__name__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        name: {key: value for key, value in {
                            "type": param.type,
                            "description": param.description,
                            "default": param.default if hasattr(param, 'default') else None,
                            "enum": param.enum if param.enum else None
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
            return func
        return decorator

    def _setup_routes(self):
        logging.debug("Setting up routes")
        def route_handler():
            data = request.json
            
            if data.get('action') == "get_signature":
                return self._handle_signature_request(data)

            return self._handle_function_call(data)

        if self.auth:
            route_handler = self.auth.verify_password(route_handler)
        
        self.app.route('/swaig', methods=['POST'])(route_handler)
    
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
        return jsonify(signatures)
    
    def _handle_function_call(self, data):
        logging.debug("Handling function call with data: %s", data)
        function_name = data.get('function')
        if not function_name:
            logging.error("Function name not provided")
            return jsonify({"error": "Function name not provided"}), 400

        func = self.function_objects.get(function_name)
        if not func:
            logging.error("Function not found: %s", function_name)
            return jsonify({"error": "Function not found"}), 404

        params = data.get('argument', {}).get('parsed', [{}])[0]
        meta_data = data.get('argument', {}).get('meta_data', {})
        meta_data_token = meta_data.get('meta_data_token', {})
        logging.debug("Calling function: %s with params: %s, meta_data_token: %s, meta_data: %s", function_name, params, meta_data_token, meta_data)

        try:
            response, meta_data = func(**params, **meta_data_token, **meta_data)

            if meta_data:
                logging.debug("Function %s executed successfully with meta_data: %s", function_name, meta_data)
                return jsonify({"response": response, "actions": [{"set_meta_data": meta_data}]})
            else:
                logging.debug("Function %s executed successfully with response: %s", function_name, response)
                return jsonify({"response": response})
        except Exception as e:
            logging.error("Error executing function %s: %s", function_name, str(e))
            return jsonify({"error": str(e)}), 500

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
            
        return urlunsplit((url.scheme, netloc, url.path, url.query, url.fragment)) 