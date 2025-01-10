# PIXL pipeline database

The [PIXL database](../docs/services/pixl_database.md) is run on a [postgres](https://www.postgresql.org/)
container and the pixl_imaging api uses [alembic](https://alembic.sqlalchemy.org/) to manage migrations.
This allows a reproducible way to update (or rollback) alterations to the PIXL pipeline's database schema.

See  [/pixl_imaging/alembic](../pixl_imaging/alembic) for how these are defined and how to create new migrations.

## 'PIXL/postgres' Directory Contents

<details>
<summary>
<h3> Files </h3> 

</summary>

| **Configuration** | **Code** | **User docs** |
| :--- | :--- | :--- |
| postgres.conf | pixl-db_init.sh | README.md |

</details>



