# PIXL Electronic Health Record Extractor

The EHR API provides an HTTP endpoint to extract EHR data from the EMAP star database and export it
as parquet files. It expects a JSON-formatted message as input, structured as defined by the
[`Message`](../pixl_core/src/core/patient_queue/message.py) class in `pixl_core/patient_queue`.
Upon receiving a message, the API will extract the EHR data for the patient specified in the message
and anonymise any identifiable data through the [CogStack](https://cogstack.org/) API.

## Installation

First, make sure you have `postgresql` installed on your system.

On macOS:

```bash
brew install postgresql
```

On Ubuntu:

```bash
sudo apt install postgresql
```

On Windows, follow [these instructions](https://www.postgresqltutorial.com/postgresql-getting-started/install-postgresql/).

Then install the Python dependencies with

```bash
pip install -e ../pixl_core/ .
```

## Test

```bash
pip install -e ../pixl_core/[test] .[test]
pytest -m "not processing"
```

and the processing tests with

```bash
./tests/run-processing-tests.sh
```

To test the availability of a CogStack instance, we mock up a *FastAPI* server which simply takes in
some input text and returns the text with a fixed suffix. The mocking is handled by a *pytest* fixture in
`test_processing.py()` (`_mock_requests`).

## Usage

Usage should be from the CLI driver, which calls the HTTP endpoints.

## Notes

- The height/weight/GCS value is extracted only within a 24 h time window
