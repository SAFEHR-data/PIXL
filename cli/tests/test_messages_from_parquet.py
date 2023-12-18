from pixl_cli.main import messages_from_parquet


def test_messages_from_parquet(resources):
    omop_parquet_dir = resources / "omop"
    messages = messages_from_parquet(omop_parquet_dir)
    expected_messages = [
        b'{"mrn": "12345678", "accession_number": "12345678", "study_datetime": "2021-'
        b'07-01", "procedure_occurrence_id": 1}',
        b'{"mrn": "12345678", "accession_number": "ABC1234567", "study_datetime": "202'
        b'1-07-01", "procedure_occurrence_id": 2}',
        b'{"mrn": "987654321", "accession_number": "ABC1234560", "study_datetime": "20'
        b'20-05-01", "procedure_occurrence_id": 3}',
        b'{"mrn": "5020765", "accession_number": "MIG0234560", "study_datetime": "2015'
        b'-05-01", "procedure_occurrence_id": 4}',
    ]

    assert messages == expected_messages
