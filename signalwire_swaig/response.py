from typing import Any, Dict, List

class SWAIGResponse:
    def __init__(self, response: Any = None):
        self.response = response
        self.actions: List[Dict[str, Any]] = []

    def set_response(self, response: Any):
        self.response = response

    def add_action(self, action_type: str, value: Any):
        self.actions.append({action_type: value})

    def to_dict(self) -> Dict[str, Any]:
        resp = {"response": self.response}
        if self.actions:
            resp["action"] = self.actions
        return resp 