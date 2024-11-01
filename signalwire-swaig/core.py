from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from urllib.parse import urlsplit, urlunsplit
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass

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
                "function": func.__name__,
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
        def route_handler():
            data = request.json
            
            if data.get('action') == "get_signature":
                return self._handle_signature_request(data)
            return self._handle_function_call(data)

        if self.auth:
            route_handler = self.auth.verify_password(route_handler)
        
        self.app.route('/swaig', methods=['POST'])(route_handler)
    
    def _handle_signature_request(self, data):
        requested = data.get("functions") or list(self.functions.keys())
        base_url = self._get_base_url()
        
        return jsonify([
            {**self.functions[name], "web_hook_url": f"{base_url}/swaig"}
            for name in requested
            if name in self.functions
        ])
    
    def _handle_function_call(self, data):
        function_name = data.get('function')
        if not function_name or function_name not in self.functions:
            return jsonify({"error": "Function not found"}), 404
            
        params = data.get('argument', {}).get('parsed', [{}])[0]

        try:
            func = globals()[function_name]
            response = func(**params)
            return jsonify({"response": response })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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