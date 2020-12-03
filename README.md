# AristaFlow-PY


## Examples 
The usage of all AristaFlow-PY functions requires an
`AristaFlowClientPlatform` with a valid `Configuration`. These can be
defined globally and used for all function calls.
```python
from aristaflow.client_platform import AristaFlowClientPlatform
from aristaflow.configuration import Configuration

arf_conf = Configuration(
    base_url=arf_base_url,
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
    cs = arf_platform.get_client_service()

    ws = cs.worklist_service
    return ws.get_worklist()
```