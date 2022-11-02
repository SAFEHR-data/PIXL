from patient_queue.subscriber import PixlConsumer
from patient_queue.subscriber import DicomConsumer
from patient_queue.subscriber import EhrConsumer
from patient_queue.subscriber import OrthancConsumer


def test_create_pixl_subscriber() -> None:
    """Checks whether Producer class can be instantiated"""
    assert PixlConsumer(topic_name="test", namespace="public", tenant="default", subscription_name="test-pixl") is not None


def test_create_dicom_subscriber() -> None:
    """Checks whether Producer class can be instantiated"""
    assert DicomConsumer(topic_name="test", namespace="public", tenant="default", subscription_name="test-dicom") is not None


def test_create_ehr_subscriber() -> None:
    """Checks whether Producer class can be instantiated"""
    assert EhrConsumer(topic_name="test", namespace="public", tenant="default", subscription_name="test-ehr") is not None


def test_create_orthanc_subscriber() -> None:
    """Checks whether Producer class can be instantiated"""
    assert OrthancConsumer(topic_name="test", namespace="public", tenant="default", subscription_name="test-orth") is not None


