# Serialization helpers for Pydantic models
from __future__ import annotations

# Import datetime for timestamp conversion
from datetime import datetime

# Import Any for type hinting
from typing import Any

# Import Pydantic base model for type checking
from pydantic import BaseModel

# Convert a Pydantic model into a MongoDB-ready dictionary
def dump_model(model: BaseModel) -> dict[str, Any]:

    # Standard Pydantic serialization of the model
    doc = model.model_dump(mode="json", exclude_none=False)

    # Identify fields that likely contain Zulu timestamps based on their name
    timestamp_fields = [k for k in doc.keys() if k.endswith("_at") and isinstance(doc[k], str)]

    # Iterate through each identified timestamp field for conversion
    for field in timestamp_fields:

        # Attempt to create a MongoDB-compatible datetime object
        try:

            # Retrieve the raw timestamp string value
            val = doc[field]

            # Proceed if the value is not empty
            if val:

                # Replace Zulu 'Z' suffix with an explicit UTC offset
                clean_val = val.replace("Z", "+00:00")

                # Parse the string into a native Python datetime object
                doc[f"{field}__d"] = datetime.fromisoformat(clean_val)

        # Skip conversion if the field value does not match the ISO format
        except (ValueError, TypeError):

            # Silently continue to the next field
            continue

    # Return the dictionary with both string and object timestamp formats
    return doc
