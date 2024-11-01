from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from urllib.parse import urlsplit, urlunsplit
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
import logging

# Set up basic logging configuration
logging.basicConfig(level=logging.DEBUG)

@dataclass
class Parameter:
    type: str
    description: str
    required: bool = True

class SWAIG:
    def __init__(self, app: Flask, auth: Optional[tuple[str, str]] = None):
        """Initialize SWAIG with Flask app and optional auth credentials.
        
        Args:
            app: Flask application instance
            auth: Tuple of (username, password) for basic auth, or None
        """
        logging.debug("Initializing SWAIG with app: %s and auth: %s", app, auth)
        self.app = app
        self.auth = HTTPBasicAuth() if auth else None
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.auth_creds = auth
        
        self._setup_routes()
    
    def endpoint(self, description: str, **params: Parameter):
        """Decorator to register a SWAIG endpoint with parameters.
        
        Example:
            @swaig.endpoint("Check insurance eligibility",
                member_id=Parameter("string", "Member ID number"),
                provider=Parameter("string", "Insurance provider name"))
            def check_insurance(member_id, provider):
                return f"Checking insurance for {member_id} with {provider}"
        """
        def decorator(func: Callable):
            self.functions[func.__name__] = {
                "description": description,
                "function": func,  # Store the function object
                "parameters": {
                    "type": "object",
                    "properties": {
                        name: {"type": param.type, "description": param.description}
                        for name, param in params.items()
                    },
                    "required": [
                        name for name, param in params.items()
                        if param.required
                    ]
                }
            }
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
                func_info.pop("function", None)  # Exclude the function object
                signatures.append(func_info)
        return jsonify(signatures)
    
    def _handle_function_call(self, data):
        logging.debug("Handling function call with data: %s", data)
        function_name = data.get('function')
        if not function_name or function_name not in self.functions:
            logging.error("Function not found: %s", function_name)
            return jsonify({"error": "Function not found"}), 404

        params = data.get('argument', {}).get('parsed', [{}])[0]
        logging.debug("Calling function: %s with params: %s", function_name, params)

        try:
            func_info = self.functions.get(function_name)
            if not func_info:
                logging.error("Function not found in registered functions: %s", function_name)
                return jsonify({"error": "Function not found"}), 404

            func = func_info['function']  # Retrieve the function object
            if not func:
                logging.error("Function object not found for: %s", function_name)
                return jsonify({"error": "Function object not found"}), 404

            response = func(**params)
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