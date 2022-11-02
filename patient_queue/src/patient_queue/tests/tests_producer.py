from patient-queue.producer import PixlProducer


def test_create() -> None:
    assert PixlProducer() is not None