import math
import numpy as np


def jsonable(o):
    """Recursively convert numpy / NaN / inf into strict-JSON-safe values."""
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    if isinstance(o, np.generic):
        return jsonable(o.item())
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o