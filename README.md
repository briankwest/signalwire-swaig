# SignalWire SWAIG

SignalWire SWAIG is a Python package that provides an interface for AI Agents to interact with SignalWire services. This package is designed to simplify the integration of AI capabilities with SignalWire's robust communication platform.

## Features

- Easy integration with SignalWire services
- Designed for AI Agents
- Lightweight and efficient

## Installation

To install SignalWire SWAIG, use pip:

```bash
pip install signalwire-swaig
```


## Usage

### Basic Setup

1. **Initialize SWAIG with a Flask app**:

   ```python
   from flask import Flask
   from signalwire_swaig.core import SWAIG

   app = Flask(__name__)
   swaig = SWAIG(app)
   ```

2. **Define an Endpoint**:

   Use the `@swaig.endpoint` decorator to define an API endpoint.

   ```python
   from signalwire_swaig.core import Parameter

   @swaig.endpoint("Check insurance eligibility",
                   member_id=Parameter("string", "Member ID number"),
                   provider=Parameter("string", "Insurance provider name"))
   def check_insurance(member_id, provider):
       return f"Checking insurance for {member_id} with {provider}"
   ```

3. **Run the Flask App**:

   ```python
   if __name__ == '__main__':
       app.run()
   ```

### Authentication

To enable basic authentication, provide a tuple of `(username, password)` when initializing SWAIG:


```python
swaig = SWAIG(app, auth=("username", "password"))
```

### Endpoint Details

- **Description**: A brief description of what the endpoint does.
- **Parameters**: Define the parameters with their type, description, and whether they are required.

### Handling Requests

- **Get Signature**: Send a POST request to `/swaig` with `{"action": "get_signature"}` to retrieve the API signature.
- **Function Call**: Send a POST request to `/swaig` with `{"function": "function_name", "argument": {"parsed": [{"param1": "value1", ...}]}}` to call a registered function.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any improvements or bug fixes.

## Contact

For any questions or support, please contact [brian@signalwire.com](mailto:brian@signalwire.com).
