from signalwire_swaig.swaig import SWAIG, SWAIGArgument, SWAIGArgumentItems, SWAIGFunctionParams
from flask import Flask

app = Flask(__name__)
swaig = SWAIG(app)

@swaig.endpoint(
    "Demonstrates all OpenAI-supported parameter data types",
    SWAIGFunctionParams(
    ),
    string_example=SWAIGArgument(
        type="string",
        description="A simple string value",
        required=True
    ),
    integer_example=SWAIGArgument(
        type="integer",
        description="An integer value",
        required=True
    ),
    number_example=SWAIGArgument(
        type="number",
        description="A floating point number"
    ),
    boolean_example=SWAIGArgument(
        type="boolean",
        description="A true/false boolean value",
        required=True
    ),
    enum_example=SWAIGArgument(
        type="string",
        description="A value constrained to a specific set of strings",
        enum=["option1", "option2", "option3"]
    ),
    array_example=SWAIGArgument(
        type="array",
        description="An array of strings",
        items=SWAIGArgumentItems(type="string")
    ),
    object_example=SWAIGArgument(
        type="object",
        description="A nested object with internal fields",
        items=SWAIGArgumentItems(
            type="object",
            properties={
                "nested_string": SWAIGArgument(
                    type="string",
                    description="A nested string",
                    required=True
                ),
                "nested_number": SWAIGArgument(
                    type="number",
                    description="A nested number"
                )
            },
            required=["nested_string"]
        )
    ),
    array_of_objects=SWAIGArgument(
        type="array",
        description="An array of structured objects",
        items=SWAIGArgumentItems(
            type="object",
            properties={
                "name": SWAIGArgument(
                    type="string",
                    description="Name of the item",
                    required=True
                ),
                "value": SWAIGArgument(
                    type="integer",
                    description="Numeric value of the item",
                    required=True
                )
            },
            required=["name", "value"]
        )
    )
)
def example_tool_with_all_data_types(
    string_example,
    integer_example,
    number_example=None,
    boolean_example=None,
    enum_example=None,
    array_example=None,
    object_example=None,
    array_of_objects=None,
    meta_data=None,
    meta_data_token=None
):
    """
    Returns a summary of the received parameters for demonstration.
    """
    summary = f"Received: string_example={string_example}, integer_example={integer_example}, number_example={number_example}, boolean_example={boolean_example}, enum_example={enum_example}, array_example={array_example}, object_example={object_example}, array_of_objects={array_of_objects}, meta_data={meta_data}, meta_data_token={meta_data_token}"
    return summary, {}

# If running as main, start the Flask app
if __name__ == "__main__":
    app.run(debug=True)