#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from pathlib import Path

import pytest
from pixl_ehr.report_deid.deid import (
    _remove_any_excluded_words,
    _remove_any_trailing_tags,
    _remove_case_insensitive_patterns,
    _remove_case_sensitive_patterns,
    _remove_linebreaks_after_title_case_lines,
    deidentify_text,
)

THIS_DIR = Path(Path.parent(Path.resolve(__file__)))


def _patient_names_from_names_csv() -> list[tuple[str, str]]:
    """From a csv file with a header and an index column extract name tuples"""

    def _tuple_from(line: str) -> tuple[str, str]:
        items = line.split(",")
        return items[1], items[2]

    path = THIS_DIR / "data" / "names.csv"

    return [_tuple_from(line) for line in Path.open(path).readlines()[1:]]


def test_patient_name_is_redacted(required_accuracy: float = 0.85) -> None:
    results = []

    for first_name, last_name in _patient_names_from_names_csv():
        report_text = f"{first_name} {last_name} was x-rayed and the prognosis is X"
        anon_text = deidentify_text(report_text)
        results.append(first_name not in anon_text and last_name not in anon_text)

    accuracy_ratio = sum(results) / len(results)
    assert accuracy_ratio > required_accuracy


def test_signed_by_section_is_removed() -> None:
    first_name, last_name, date = info = "John", "Doe", "01/01/20"

    anon_text = deidentify_text(
        f"A xray report with information\n"
        f"Signed by:\n{first_name} {last_name}\n{date}"
    )

    assert all(s not in anon_text for s in info)


@pytest.mark.parametrize("id_name", ["GMC", "HCPC"])
def test_block_with_excluded_identifiers_are_removed(id_name: str) -> None:
    header, footer = "A xray report with information", "Other text"
    first_name, last_name, num = info = "John", "Doe", "0123456"

    anon_text = deidentify_text(
        f"{header}\n"
        "\n"
        f"{first_name} {last_name}\n"
        f"{id_name}: \n"
        "University College London Hospital\n"
        "\n"
        f"{footer}"
    )

    assert all(s not in anon_text for s in info)
    assert header in anon_text
    assert footer in anon_text


# using ":" or " " as a delimiter is not redacted by Presidio
@pytest.mark.parametrize("delimiter", ["/", "-"])
def test_possible_dates_are_removed(delimiter: str) -> None:
    for day, month, year in [(1, 3, 2019)]:
        date_strings = [
            f"{day}{delimiter}{month}{delimiter}{year}",
            f"{month}{delimiter}{day}{delimiter}{year}",
            f"{year}{delimiter}{month}{delimiter}{day}",
            f"{day:02d}{delimiter}{month:02d}{delimiter}{year}",  # +leading 0
        ]

        anon_text = deidentify_text("\n".join(date_strings))
        assert not any(date_string in anon_text for date_string in date_strings)


def test_accession_nums_gmc_nhs_email() -> None:
    gmc_number = "12345"
    email_address = "jon.smith@nhs.net"
    accession_number = "RRV012734923"

    text = (
        f"Accession No. {accession_number}. Some other text. "
        f"GMC: {gmc_number}. X NHS trust {email_address}"
    )
    re_anon_text = _remove_case_insensitive_patterns(text)

    for identifier in (gmc_number, email_address, accession_number):
        assert identifier not in re_anon_text

    assert "Some other text" in deidentify_text(text)  # Need to retain some text


def test_linebreaks_are_removed_from_possible_identifying_section() -> None:
    text = "A report.\nJohn Smith\nReporting Radiographer\nOther text after"
    expected_text = "A report.\nJohn Smith Reporting Radiographer Other text after"

    assert _remove_linebreaks_after_title_case_lines(text) == expected_text


@pytest.mark.parametrize("initials", ["JS", "AJ", "AO\t", "ER "])
def test_initials_are_removed_from_end_of_string(initials: str) -> None:
    text = f"Some text. {initials}"
    assert initials.strip() not in _remove_case_sensitive_patterns(text)


def test_allow_list_is_not_removed_from_sentence() -> None:
    assert "NG" in deidentify_text("A thing with XR. For NG things")


@pytest.mark.parametrize("full_name", ["John Doe-Smith"])
def test_full_name_with_hypens_is_removed(full_name: str) -> None:
    _assert_neither_name_in_text(
        full_name=full_name,
        text=_remove_case_sensitive_patterns(f"A sentence  {full_name} registrar"),
    )


@pytest.mark.parametrize(
    "full_name", ["John Doe SMITH", "<PERSON>, SMITH", "SMITH, JOHN", "SMITH, John"]
)
def test_full_name_after_signed_by_is_removed(full_name: str) -> None:
    _assert_neither_name_in_text(
        full_name=full_name,
        text=_remove_case_sensitive_patterns(f"Things. Signed by: {full_name}"),
    )


@pytest.mark.parametrize("full_name", ["John SMITH"])
def test_full_name_after_comma_is_removed(full_name: str) -> None:
    _assert_neither_name_in_text(
        full_name=full_name,
        text=_remove_case_sensitive_patterns(f"Things, {full_name}"),
    )


def _assert_neither_name_in_text(full_name: str, text: str) -> None:
    for name in full_name.split():
        assert name not in text


@pytest.mark.parametrize("name", ["Zebadiah", "TOM", "roger"])
def test_name_from_exclusion_list_is_removed(name: str) -> None:
    assert name not in _remove_any_excluded_words(f"Someone {name} and other")


@pytest.mark.parametrize("date_str", ["14 Jun 2022", "1 Jan 2022", "21 March 2022"])
def test_abbreviated_date_is_removed(date_str: str) -> None:
    text = f"A sentence {date_str} then other things"
    assert date_str not in _remove_case_insensitive_patterns(text)


def test_remove_trailing_tags() -> None:
    text = "A sentence XXX> other things"
    expected_text = "A sentence XXX other things"
    assert _remove_any_trailing_tags(text) == expected_text


@pytest.mark.parametrize("digits_str", ["14", "01", "7", "31"])
def test_remove_up_to_two_digits_before_datetime(digits_str: str) -> None:
    text = f"A sentence referring to {digits_str} <DATE_TIME> then other text"
    assert digits_str not in _remove_case_insensitive_patterns(text)
