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
                   member_id=Parameter("string", "Member ID number", required=True),
                   provider=Parameter("string", "Insurance provider name", required=True))
   def check_insurance(member_id, provider):
       return f"Checking insurance for {member_id} with {provider}"
   ```

3. **Run the Flask App**:

   ```python
   if __name__ == '__main__':
       app.run()
   ```

### Advanced Parameter Usage

You can define parameters with additional attributes like `required`, `enum`, and `default`.

```python
from signalwire_swaig.core import Parameter

@swaig.endpoint("Get user details",
                user_id=Parameter("string", "User ID", required=True),
                role=Parameter("string", "User role", enum=["admin", "user", "guest"]),
                status=Parameter("string", "Account status", default="active"))
def get_user_details(user_id, role="user", status="active"):
    return f"User {user_id} is a {role} with status {status}"
```

- **`required`**: Indicates if the parameter is mandatory. If not provided, the request will be rejected.
- **`enum`**: Specifies a list of acceptable values for the parameter. If the provided value is not in the list, the request will be rejected.
- **`default`**: Provides a default value for the parameter if it is not supplied in the request.

### SWAIGArgument and SWAIGArgumentItems

`SWAIGArgument` and `SWAIGArgumentItems` are used to define complex argument structures for your endpoints.

- **`SWAIGArgument`**: Represents a single argument with a specific type and description.
- **`SWAIGArgumentItems`**: Represents a collection of `SWAIGArgument` objects, allowing you to define nested or grouped parameters.

Example usage:

```python
from signalwire_swaig.core import SWAIGArgument, SWAIGArgumentItems

@swaig.endpoint("Process order",
                order=Parameter("object", "Order details", required=True, items=SWAIGArgumentItems(
                    SWAIGArgument("product_id", "string", "Product ID", required=True),
                    SWAIGArgument("quantity", "integer", "Quantity of the product", required=True),
                    SWAIGArgument("color", "array", "Color of the product", required=True, items=SWAIGArgumentItems(
                        SWAIGArgument("type", "string", "Type of the product", enum=["shirt", "pants", "shoes"])
                    )
                )))
def process_order(order):
    return f"Processing order for product {order['product_id']} with quantity {order['quantity']} at {order['price']} each"
```

- **`SWAIGArgument`**: Define each argument with its type, description, and whether it is required.
- **`SWAIGArgumentItems`**: Use this to group multiple `SWAIGArgument` objects together for complex parameter structures.

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
