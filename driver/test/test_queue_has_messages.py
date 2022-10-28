import os
from requests import request


def test_queue_is_up():

    res = request("GET", "http://localhost:8080/admin/v2/brokers/health")
    assert res.status_code == 200


def test_upping_driver_adds_a_single_item_to_the_queue():

    _delete_all_topics()
    os.system("docker compose --env-file .env.test up driver")

    for topic_name in _topic_names():
        res = request("GET", f"http://localhost:8080/admin/v2/persistent/"
                             f"public/default/{topic_name}/internalStats")
        assert res.status_code == 200
        assert res.json()["entriesAddedCounter"] == 1


def _delete_all_topics():
    for topic_name in _topic_names():
        _ = request("DELETE", f"https://pulsar.apache.org/admin/v2/persistent/"
                              f"public/default/{topic_name}")


def _topic_names():
    return (os.environ["PIXL_PULSAR_EHR_TOPIC_NAME"],
            os.environ["PIXL_PULSAR_PACS_TOPIC_NAME"])
