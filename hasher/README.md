# Hasher API


_The secure hashing service_

## Local development
### Dependencies 
It is assumed you have a Python virtual environment configured using a tool like Conda or pyenv.  
Install the dependencies from inside the _PIXL/hasher/src_ directory:
```bash
pip install -r requirements.txt
```

### Run
from the _PIXL/hasher/src_ directory:
```bash
PIXL_ENV=dev uvicorn hasher.main:app --host=0.0.0.0 --port=8000 --reload
```

### Test
from the _PIXL/hasher/src_ directory:
```bash
bin/run-tests.sh
```
or
```bash
PIXL_ENV=test pytest --ff hasher/tests
```
to skip linting and run only the last failed test.
