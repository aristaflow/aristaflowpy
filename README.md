# AristaFlow BPM Python Integration

Python integration for the [AristaFlow BPM Platform](https://www.aristaflow.com/bpm-platform.html)
making it easy to use workflow features like task lists in Python applications.
Pre-build packages can be installed directly from PyPI: https://pypi.org/project/aristaflowpy/

## Examples
The usage of all AristaFlow-PY functions requires an
`AristaFlowClientPlatform` with a valid `Configuration`. These can be
defined globally and used for all function calls.
```python
from aristaflow.client_platform import AristaFlowClientPlatform
from aristaflow.configuration import Configuration

arf_conf = Configuration(
    base_url='https://aristaflow-bpm.example.com',
    caller_uri="http://localhost/python",
    application_name=None
)
arf_platform = AristaFlowClientPlatform(arf_conf)
```

### Get User Worklist
```python
def get_worklist(user, password):
    arf_cs = arf_platform.get_client_service()
    arf_cs.authenticate(user, password)

    ws = arf_cs.worklist_service
    return ws.get_worklist()
```

## Development
Automatic code formatting and import sorting using the pre-commit package is required.
- Install the `pre-commit` package in your python environment
- Install the pre-commit hook: `pre-commit install`
