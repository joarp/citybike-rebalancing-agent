import inspect
import math
import pandas as pd
from typing import Any, Dict

def _is_nan(x: Any) -> bool:
    return isinstance(x, float) and math.isnan(x)

def coerce_value(value: Any, type_tag: str):
    """
    Convert JSON-friendly values to Python objects based on a small set of type tags.
    """
    if value is None:
        return None
    if _is_nan(value):
        return None

    if type_tag == "int":
        return int(value)
    if type_tag == "float":
        return float(value)
    if type_tag == "str":
        return str(value)
    if type_tag == "dict":
        if not isinstance(value, dict):
            raise TypeError(f"Expected dict, got {type(value)}")
        return value
    if type_tag == "list":
        if not isinstance(value, list):
            raise TypeError(f"Expected list, got {type(value)}")
        return value

    # Common ML/agent types:
    if type_tag == "dataframe_records":
        # Expect list[dict] or dict with "records"
        if isinstance(value, list):
            return pd.DataFrame(value)
        if isinstance(value, dict) and "records" in value and isinstance(value["records"], list):
            return pd.DataFrame(value["records"])
        raise TypeError(f"Expected list[dict] for dataframe_records, got {type(value)}")

    # Fallback: no coercion
    return value

def coerce_args(args: Dict[str, Any], arg_types: Dict[str, str]) -> Dict[str, Any]:
    """
    Coerce args based on arg_types mapping. Only coerces keys that appear in arg_types.
    """
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise TypeError(f"Tool args must be a dict, got {type(args)}")

    coerced = dict(args)
    for k, type_tag in arg_types.items():
        if k in coerced:
            coerced[k] = coerce_value(coerced[k], type_tag)

    # sanitize NaNs anywhere at top-level
    for k, v in list(coerced.items()):
        if _is_nan(v):
            coerced[k] = None

    return coerced

def validate_args_against_signature(fn, args: Dict[str, Any]):
    sig = inspect.signature(fn)
    params = sig.parameters

    unexpected = [k for k in args.keys() if k not in params]
    if unexpected:
        raise ValueError(f"Unexpected args for {fn.__name__}: {unexpected}")

    missing = []
    for name, p in params.items():
        if p.default is inspect._empty and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
            if name not in args:
                missing.append(name)
    if missing:
        raise ValueError(f"Missing required args for {fn.__name__}: {missing}")
