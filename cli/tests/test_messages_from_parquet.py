from pixl_cli.main import messages_from_parquet


def test_messages_from_parquet(resources):
    omop_parquet_dir = resources / "omop"
    messages = messages_from_parquet(omop_parquet_dir)
    expected_messages = [
        b'{"mrn": "12345678", "accession_number": "12345678", "study_datetime": "2021-07-01", '
        b'"procedure_occurrence_id": 1}',
        b'{"mrn": "12345678", "accession_number": "ABC1234567", "study_datetime": "2021-07-01", '
        b'"procedure_occurrence_id": 2}',
        b'{"mrn": "987654321", "accession_number": "ABC1234560", "study_datetime": "2020-05-01", '
        b'"procedure_occurrence_id": 3}',
        b'{"mrn": "5020765", "accession_number": "MIG0234560", "study_datetime": "2015-05-01", '
        b'"procedure_occurrence_id": 4}',
    ]

    assert messages == expected_messages
