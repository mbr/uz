from operator import attrgetter

import click
import subprocess


from .analysis import unravel, get_command


show_info = False


def info(msg):
    if show_info:
        click.echo(msg, err=True)


@click.command()
@click.option('-A', '--analyze-only', is_flag=True)
@click.option('-D', '--debug', is_flag=True)
@click.option('-l', '--list', 'action', flag_value='list')
@click.option('-x', '--extract', 'action', flag_value='extract', default=True)
@click.argument('files', nargs=-1, type=click.File(mode='rb', lazy=False))
def uz(files, analyze_only, debug, action='extract'):
    global show_info
    show_info = debug or analyze_only

    for file in files:
        nesting = unravel(file)

        info('{}: {}'.format(
            file.name, ' <- '.join(map(attrgetter('name'), nesting))
        ))

        if not nesting:
            continue

        cmds = get_command(nesting, action, file.name)
        info('cmd: {}'.format(' | '.join(' '.join(args) for args in cmds)))

        if analyze_only:
            return

        if not nesting[-1].archive:
            raise RuntimeError('Non-archive extraction unsupported atm')

        stdin = file
        file.seek(0)
        while cmds:
            cmd = cmds.pop(0)
            stdout = subprocess.PIPE if cmds else None

            proc = subprocess.Popen(cmd, stdin=stdin, stdout=stdout)
            stdin = proc.stdout

        # wait for extraction to complete
        proc.wait()
