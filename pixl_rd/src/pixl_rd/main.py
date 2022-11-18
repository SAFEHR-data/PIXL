#  Copyright (c) University College London Hospitals NHS Foundation Trust and Microsoft
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
# limitations under the License.
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_anonymizer = AnonymizerEngine()
_analyzer = AnalyzerEngine()


def deidentify_text(text: str) -> str:
    """
    Given a string of text use presidio (https://github.com/microsoft/presidio)
    to remove patient identifiable information (PII). There is no guarantee
    that this will remove all PII.

    Args:
        text: Text to identify

    Returns:
        De-identified text
    """

    for anonymize_step in (
        _remove_all_text_below_signed_by_section,
        _remove_section_with_identifiable_id_numbers,
    ):
        text = anonymize_step(text)

    results = _analyzer.analyze(
        text=text, entities=None, language="en"  # Search for all PII
    )

    result = _anonymizer.anonymize(text=text, analyzer_results=results)
    return str(result.text)


def _remove_all_text_below_signed_by_section(text: str) -> str:

    lines = text.split("\n")

    try:
        idx_of_line_with_signed_by_in = next(
            i for i, line in enumerate(lines) if "signed by" in line.lower()
        )
    except StopIteration:  # Found no lines with "signed by" in
        return text

    return "\n".join(lines[:idx_of_line_with_signed_by_in])


def _remove_section_with_identifiable_id_numbers(text: str) -> str:
    """
    Remove a section of text with the form e.g.::

        John Doe
        GMC: 0123456
        University College London Hospital

    with a newline above and below.
    """
    exclusions = ["GMC", "HCPC"]

    return "\n\n".join(
        s for s in text.split("\n\n") if not any(exc in s for exc in exclusions)
    )
