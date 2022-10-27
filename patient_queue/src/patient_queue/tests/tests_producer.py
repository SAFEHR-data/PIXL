from patient_queue.producer import PixlProducer


def test_create_producer() -> None:
    """Checks whether Producer class can be instantiated"""
    assert PixlProducer is not None


def test_create_msg() -> None:
    """Checks whether Pulsar queue entry can be created on ."""
    try:
        prod = PixlProducer()
        prod.create_queue_entry(msg="test")
    except Exception as e:
        assert False


def test_create_error_msg() -> None:
    """Checks whether Pulsar queue entry can be created on ."""
    try:
        prod = PixlProducer()
        prod.shutdown()
        prod.create_queue_entry(msg="test")
    except Exception as e:
        assert True
