# mireva-sdk

Pure HTTP client for the MIREVA claim fraud inference API.

Install:

```bash
pip install mireva-sdk
# or from this directory:
pip install -e .
```

Usage:

```python
from mireva_sdk import MirevaClient, MirevaClaimInput

client = MirevaClient(
    base_url="http://127.0.0.1:4657",
    api_key="mv_live_....your.key",
    model_version="mireva-origin",
)

result = client.predict(claim)  # MirevaClaimInput or dict
print(result.final_decision, result.model_version)
```

This package has **no** dependency on `mireva`, `mireva_core`, PyTorch, or FastAPI.
It only performs HTTP requests and validates wire JSON with Pydantic.
