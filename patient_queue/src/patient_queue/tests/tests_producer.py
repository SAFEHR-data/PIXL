from patient_queue.producer import PixlProducer


def test_create() -> None:
    """Checks that PIXL producer can be instantiated."""
    pp = PixlProducer(_queue="test")
    assert pp is not None
    pp.shutdown()


def test_create_msg() -> None:
    """Checks that message can be produced on respective queue."""
    pp = PixlProducer(_queue="test")
    try:
        pp.create_entry(msg="hello world")
        assert True
    except Exception:
        assert False
