from operator import attrgetter

import click


from .analysis import unravel


@click.command()
@click.option('-A', '--analyze-only', is_flag=True)
@click.argument('files', nargs=-1, type=click.File(mode='rb', lazy=False))
def uz(files, analyze_only):
    for file in files:
        if analyze_only:
            an = unravel(file)

            click.echo('{}: {}'.format(
                file.name, ' <- '.join(map(attrgetter('name'), an))
            ))
