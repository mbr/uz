import io
from operator import attrgetter
import subprocess

import click

from .analysis import unravel, get_command


show_info = False


def info(msg):
    if show_info:
        click.echo(msg, err=True)


def warn(msg):
    click.echo('warning: ' + msg, err=True)


@click.command()
@click.option('-A', '--analyze-only', is_flag=True)
@click.option('-D', '--debug', is_flag=True)
@click.option('-v', '--verbose', is_flag=True)
@click.option('-l', '--list', 'action', flag_value='list')
@click.option('-x', '--extract', 'action', flag_value='extract', default=True)
@click.argument('files', nargs=-1,
                type=click.Path(dir_okay=False, exists=True))
def uz(files, analyze_only, debug, verbose, action='extract'):
    global show_info
    show_info = debug or analyze_only

    cmd_args = {
        'verbose': verbose,
    }

    for fn in files:
        file = io.open(fn, 'rb')
        nesting = unravel(file)

        info('{}: {}'.format(
            file.name, ' <- '.join(map(attrgetter('name'), nesting))
        ))

        if not nesting:
            continue

        if len(nesting) > 1 and not nesting[-1].streamable:
            nesting.pop()
            warn('cannot unpack zip archive from stream, need to run twice')

        cmds = get_command(nesting, action, cmd_args, file.name)
        info('cmd: {}'.format(' | '.join(' '.join(args) for args in cmds)))

        if analyze_only:
            return 0

        if not nesting[-1].archive:
            raise RuntimeError('Non-archive extraction unsupported atm')


        # repoen
        stdin = open(fn, 'rb')
        stdin.seek(0)
        while cmds:
            cmd = cmds.pop(0)
            stdout = subprocess.PIPE if cmds else None

            proc = subprocess.Popen(cmd, stdin=stdin, stdout=stdout)
            stdin = proc.stdout

        # wait for extraction to complete
        proc.wait()
