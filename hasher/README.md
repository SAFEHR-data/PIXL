# Hasher API
_The secure hashing service_


## Local development
### requirements.txt
Ensure you have the requirements from _FlowEHR/PIXL/hasher/src/requirements.txt_ installed.

### Run
from the _FlowEHR/PIXL/hasher/src_ directory:
```bash
PIXL_ENV=dev uvicorn hasher.main:app --host=0.0.0.0 --port=8000 --reload
```

### Test
TODO