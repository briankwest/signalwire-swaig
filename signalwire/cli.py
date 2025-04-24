#!/usr/bin/env python3
import argparse
import requests
import json
import sys
from requests.exceptions import RequestException

def handle_response(response):
    """Handle HTTP response and common errors"""
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print("Error: Authentication failed. Please check your credentials.")
        elif response.status_code == 403:
            print("Error: Access forbidden. Please check your permissions.")
        elif response.status_code == 404:
            print("Error: Endpoint not found. Please check the URL.")
        else:
            print(f"Error: HTTP {response.status_code} - {str(e)}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON response from server")
        print("Response content:", response.text)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def get_signatures(url, function_names):
    """Get function signatures from the SWAIG server"""
    try:
        payload = {
            "functions": function_names,
            "action": "get_signature",
            "version": "2.0",
            "content_disposition": "function signature request",
            "content_type": "text/swaig",
            "meta_data": {},
            "meta_data_token": "swaig-cli"
        }
        response = requests.post(url, json=payload)
        return handle_response(response)
    except RequestException as e:
        print(f"Error connecting to server: {str(e)}")
        sys.exit(1)

def convert_value(value, type_name, items_type=None):
    """Convert a value to the specified type"""
    if type_name == "array":
        if not isinstance(value, list):
            value = [value]
        return [convert_value(item, items_type) for item in value]
    elif type_name == "integer":
        return int(value)
    elif type_name == "number":
        return float(value)
    elif type_name == "boolean":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    return value

def test_function(url, function_names, args, meta_data):
    """Test a specific SWAIG function"""
    try:
        signatures = get_signatures(url, function_names)
        if not signatures:
            print("Error: No function signatures received")
            sys.exit(1)

        function_signature = next((f for f in signatures if f['function'] in function_names), None)
        
        if not function_signature:
            print(f"Error: Function {function_names} not found in signatures")
            sys.exit(1)

        if args.json:
            try:
                raw_args = json.loads(args.json)
                function_args = {}
                properties = function_signature['parameters']['properties']
                
                for arg, value in raw_args.items():
                    if arg in properties:
                        arg_type = properties[arg]['type']
                        items_type = properties[arg].get('items', {}).get('type') if arg_type == "array" else None
                        function_args[arg] = convert_value(value, arg_type, items_type)
                    else:
                        function_args[arg] = value
            except json.JSONDecodeError:
                print("Error: Invalid JSON format")
                sys.exit(1)
        else:
            required_args = function_signature['parameters']['required']
            properties = function_signature['parameters']['properties']
            
            function_args = {}
            for arg, details in properties.items():
                arg_type = details['type']
                is_required = arg in required_args
                description = details.get('description', '')
                items_type = details.get('items', {}).get('type') if arg_type == "array" else None

                if arg_type == "array":
                    prompt = f"Enter {arg} (array of {items_type})"
                else:
                    prompt = f"Enter {arg} ({arg_type})"
                if description:
                    prompt += f" - {description}"
                if not is_required:
                    prompt += " [optional]"

                if arg_type == "array":
                    values = []
                    print(f"\n{prompt}")
                    print("Enter one value per line. Leave empty to finish.")
                    while True:
                        value = input(f"Enter value (or empty to finish): ")
                        if not value:
                            if not values and is_required:
                                print(f"Error: {arg} is required")
                                continue
                            break
                        try:
                            converted_value = convert_value(value, items_type)
                            values.append(converted_value)
                        except ValueError:
                            print(f"Error: Invalid {items_type} value")
                    if values:
                        function_args[arg] = values
                else:
                    while True:
                        value = input(prompt + ": ")
                        
                        if not value and is_required:
                            print(f"Error: {arg} is required")
                            continue
                        elif not value and not is_required:
                            break
                        
                        try:
                            function_args[arg] = convert_value(value, arg_type)
                            break
                        except ValueError:
                            print(f"Error: Invalid {arg_type} value")

        payload = {
            "function": function_names[0],
            "argument": {"parsed": [function_args]},
            "meta_data": meta_data or {},
            "meta_data_token": "swaig-cli"
        }
        
        print("\nSending request to server...")
        print(json.dumps(payload, indent=2))
        response = requests.post(url, json=payload)
        result = handle_response(response)
        
        print("\nServer Response:")
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="SWAIG CLI Tool - Test SignalWire AI Gateway functions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Get all function signatures:
    %(prog)s --url http://username:password@localhost:5002/swaig --get-signatures

  Get specific function signature:
    %(prog)s --url http://username:password@localhost:5002/swaig --get-signatures --function create_reservation

  Test a function:
    %(prog)s --url http://username:password@localhost:5002/swaig --function create_reservation

  Test a function with JSON arguments:
    %(prog)s --url http://username:password@localhost:5002/swaig --function search_movie --json '{"query": "Pretty Woman"}'
        """
    )
    parser.add_argument('--url', required=True, help='The SWAIG server URL (including auth if required)')
    parser.add_argument('--get-signatures', action='store_true', help='Get function signatures')
    parser.add_argument('--function', help='Test a specific function by name')
    parser.add_argument('--json', help='JSON string containing function arguments')
    parser.add_argument('--meta-data', help='Additional metadata to include in the request as a JSON string')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    function_names = args.function.split(',') if args.function else []

    if args.meta_data:
        try:
            meta_data = json.loads(args.meta_data)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for meta-data")
            sys.exit(1)
    else:
        meta_data = {}

    try:
        if args.get_signatures:
            signatures = get_signatures(args.url, function_names)
            print(json.dumps(signatures, indent=2))
        elif args.function:
            test_function(args.url, [args.function], args, meta_data)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()
