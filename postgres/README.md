# PIXL pipeline database

The PIXL database is run on a postgres container and uses [alembic](https://alembic.sqlalchemy.org/) to manage migrations.
This allows a reproducible way to update (or rollback) alterations to the PIXL pipeline's database schema.

The alembic configuration is defined in [postgres/alembic](alembic),
with each migration in [postgres/alembic/versions](alembic/versions).
