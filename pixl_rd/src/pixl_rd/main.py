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
