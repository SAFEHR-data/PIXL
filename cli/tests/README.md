# PIXL cli tests

This directory contains the code for the tests of the PIXL command line interface.



In order to remove the db container and associated data after the tests have been run use the following command:

```bash
docker container rm pixl-test-db -v -f
```

## 'PIXL/cli/tests' Directory Contents

<details>
<summary>
<h3> Files </h3> 

</summary>

| **Code** | **User docs** |
| :--- | :--- |
| conftest.py | README.md |
| test_check_env.py | |
| test_database.py | |
| test_docker_commands.py | |
| test_io.py | |
| test_messages_from_files.py | |
| test_message_processing.py | |
| test_populate.py | |

</details>

