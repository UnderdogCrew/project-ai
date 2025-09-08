from pydantic import create_model
from typing import List, Any
from uuid import uuid4


def create_dynamic_model(fields, name=None):
    final = {}
    name = name or f"DynamicModel_{uuid4().hex}"

    def build_array_type(root_item):
        """
        Build a nested List[...] type from a root array item and its
        single `nested_array_levels` list.

        The chain is:
            [root_item] + nested_array_levels
        Each element MUST have type='array'.
        The LAST element's `array_item_type` determines the base (string/int/bool/object/Any).
        Number of List[...] wrappers == len(chain).
        """
        chain = [root_item] + root_item.get("nested_array_levels", [])

        for i, lv in enumerate(chain):
            if lv.get("type") != "array":
                raise ValueError(f"nested_array_levels[{i}] must have type='array' (got {lv.get('type')!r})")

        terminal = chain[-1]
        term_item_type = terminal.get("array_item_type")

        if term_item_type == "string":
            base = str
        elif term_item_type == "integer":
            base = int
        elif term_item_type == "boolean":
            base = bool
        elif term_item_type == "object":
            base = create_dynamic_model(
                terminal["object_properties"],
                name=f"{(terminal.get('key') or 'Item').capitalize()}ItemModel"
            )
        elif term_item_type == "array":
            base = Any
        else:
            base = Any
        inner = base
        for _ in chain:
            inner = List[inner]
        return inner

    for item in fields:
        key, typ = item["key"], item["type"]

        match typ:
            case "string":
                final[key] = (str, ...)
            case "integer":
                final[key] = (int, ...)
            case "boolean":
                final[key] = (bool, ...)
            case "object":
                sub = create_dynamic_model(item["object_properties"], name=f"{key.capitalize()}Model")
                final[key] = (sub, ...)
            case "array":
                inner = build_array_type(item)
                final[key] = (inner, ...)
            case _:
                # Unknown type → Any (required)
                final[key] = (Any, ...)

    return create_model(name, **final)


if __name__ == "__main__":
    fields = [
        {"key": "domain", "type": "string"},
        {"key": "summary", "type": "string"},
        {
            "key": "customers",
            "type": "array",
            "array_item_type": "array",
            "nested_array_levels": [
                {"key": "", "type": "array", "array_item_type": "array"},
                {"key": "", "type": "array", "array_item_type": "string"},
            ],
        },
        {
            "key": "products",
            "type": "object",
            "object_properties": [
                {
                    "key": "sector",
                    "type": "object",
                    "object_properties": [
                        {"key": "name", "type": "string"}
                    ],
                }
            ],
        },
    ]

    Model = create_dynamic_model(fields)
    print(Model.model_json_schema())

    # Sanity check instance:
    m = Model(
        domain="example.com",
        summary="ok",
        # customers: root array + level1 array + level2 array → List[List[List[bool]]]
        customers=[[["Jio", "Rapido"], ["Siemens"]], [["Glance"]]],
        products={"sector": {"name": "Tech"}},
    )
    print(m.model_dump_json(indent=2))
