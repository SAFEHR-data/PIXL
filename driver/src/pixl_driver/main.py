import click


@click.group()
@click.option('--debug/--no-debug', default=False)
def main(debug):
    pass


@main.command()
@click.argument("csv_filename", type=click.Path(exists=True))
def up(csv_filename):
    click.echo(f'Populating queue from {csv_filename}')


@main.command()
def stop():
    click.echo('Stopping extraction')
