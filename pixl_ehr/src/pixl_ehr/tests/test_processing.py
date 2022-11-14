"""
These tests require executing from within the EHR API container with the dependent
services being up
    - pixl postgres db
    - emap star
"""
from pixl_ehr._processing import process_message

mrn = "a"
accession_number = "B"
study_datetime = "01/01/2022 00:01:00"

# TODO: replace with serialisation function
message_body = f"{mrn},{accession_number},{study_datetime}".encode("utf-8")


def test_message_processing():
    process_message(message_body)
