import click


from .analysis import unravel


@click.command()
@click.option('-A', '--analyze-only', is_flag=True)
@click.argument('files', nargs=-1, type=click.Path(exists=True,
                dir_okay=False))
def uz(files, analyze_only):
    for fn in files:
        print unravel(fn)
        #click.echo(fn)
