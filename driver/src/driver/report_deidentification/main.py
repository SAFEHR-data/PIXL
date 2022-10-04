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

    results = _analyzer.analyze(
        text=text, entities=None, language="en"  # Search for all PII
    )

    result = _anonymizer.anonymize(text=text, analyzer_results=results)
    return str(result.text)
