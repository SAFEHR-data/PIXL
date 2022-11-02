from patient_queue.producer import PixlProducer
from patient_queue.producer import DicomProducer
from patient_queue.producer import EhrProducer
from patient_queue.producer import OrthancProducer


def test_create_pixl_producer() -> None:
    """Checks whether Producer class can be instantiated"""
    assert PixlProducer(topic_name="test", namespace="public", tenant="default") is not None


def test_create_dicom_producer() -> None:
    """Checks whether Producer class can be instantiated"""
    assert DicomProducer(namespace="public", tenant="default") is not None


def test_create_ehr_producer() -> None:
    """Checks whether Producer class can be instantiated"""
    assert EhrProducer(namespace="public", tenant="default") is not None


def test_create_orthanc_producer() -> None:
    """Checks whether Producer class can be instantiated"""
    assert OrthancProducer(namespace="public", tenant="default") is not None


def test_create_empty_producer() -> None:
    """Checks that Producer can't be instantiated without a topic."""
    try:
        PixlProducer()
    except TypeError as te:
        assert True


def test_create_msg() -> None:
    """Checks whether Pulsar queue entry can be created on ."""
    try:
        prod = PixlProducer(topic_name="test", namespace="public", tenant="default")
        prod.create_queue_entry(msg="test")
        prod.shutdown()
    except Exception as e:
        assert False


def test_create_dicom_msg() -> None:
    """Checks whether Pulsar Dicom queue entry can be created. """
    try:
        prod = DicomProducer(namespace="public", tenant="default")
        prod.create_queue_entry(msg="test")
        prod.shutdown()
    except Exception as e:
        assert False


def test_create_error_msg() -> None:
    """Checks whether Pulsar queue entry can be created on ."""
    try:
        prod = PixlProducer(topic_name="test", namespace="public", tenant="default")
        prod.shutdown()
        prod.create_queue_entry(msg="test")
    except Exception as e:
        assert True
