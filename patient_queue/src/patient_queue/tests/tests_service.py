
def test_pulsar_up() -> None:
    # needs PULSAR_HTTP_PORT -->  i.e. http://localhost:PULSAR_HTTP_PORT/metrics/
    # if it is up and running, it gets a response 200 otherwise raises exception
    """ Checks whether the Pulsar service is up and running by attempting to access metrics. """

