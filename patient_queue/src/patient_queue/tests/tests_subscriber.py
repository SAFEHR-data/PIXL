from patient_queue.subscriber import PixlConsumer


def test_create() -> None:
    """Checks that PIXL producer can be instantiated."""
    pc = PixlConsumer(_queue="test")
    assert pc is not None
    pc.shutdown()


def test_create_msg() -> None:
    """Checks that message can be produced on respective queue."""
    pc = PixlConsumer(_queue="test")
    try:
        msg = pc.retrieve_msg()
        print(msg)
        assert True
    except Exception:
        assert False
    pc.shutdown()
