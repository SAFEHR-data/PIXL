#  Copyright (c) University College London Hospitals NHS Foundation Trust
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
import logging
import re

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_anonymizer = AnonymizerEngine()
_analyzer = AnalyzerEngine()

logger = logging.getLogger(__name__)


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
        _presidio_anonymise,
        _remove_all_text_below_signed_by_section,
        _remove_section_with_identifiable_id_numbers,
        _remove_excluded_patterns,
    ):
        text = anonymize_step(text)

    return text


def _presidio_anonymise(text: str) -> str:

    results = _analyzer.analyze(
        text=text,
        entities=["DATE_TIME", "PERSON"],
        language="en",
        allow_list=["XR Skull"],
    )

    result = _anonymizer.anonymize(text=text, analyzer_results=results)
    return str(result.text)


def _remove_all_text_below_signed_by_section(text: str) -> str:

    lines = text.split("\n")

    if _num_non_blank_lines(text) == 1:
        logger.warning(
            "Failed to remove text below signed by section. Only had one " "line"
        )
        return text

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
    if _num_non_blank_lines(text) == 1:
        logger.warning("Cannot remove below identifable by section. Only had one line")
        return text

    exclusions = ["GMC", "HCPC"]

    return "\n\n".join(
        s for s in text.split("\n\n") if not any(exc in s for exc in exclusions)
    )


def _remove_excluded_patterns(text: str) -> str:

    patterns = (
        r"(\S+@\S+)",  # Matches any email address
        r"GMC[\s\S]?: (\d+)",  # Matches GMC numbers
        r"HCPC: (\d+)",  # Matches HCPC numbers
        r"RRV(\d+)",  # Accession numbers
        r"signed by[^.]*.+",  # Matches signed by section and after
        r"[^.]* University College London Hospitals [^.]*.+",  # Sentences after UCLH
        r"(\d+[\s]?[:/][\s]\d+)",  # Date or time like things
        r"(\d{4,100})",  # Remove any long numeric values (7 is GMC)
        r"[^.]*Dr[.|\s][^.]*\.",  # Remove any sentences with Dr in
        r"(\d+[\/|:]\d+)",  # Remove any partial dates seperated by : or /
    )
    return re.sub("|".join(patterns), repl="XXX", string=text, flags=re.IGNORECASE)


def _num_non_blank_lines(text: str) -> int:
    return sum(len(line.split()) > 0 for line in text.split("\n"))
