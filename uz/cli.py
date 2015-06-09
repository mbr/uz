import io
from operator import attrgetter
import os
import subprocess

import click

from .analysis import unravel, get_command, get_filename


show_info = False


def info(msg):
    if show_info:
        click.echo(msg, err=True)


def warn(msg):
    click.echo('warning: ' + msg, err=True)


@click.command()
@click.version_option()
@click.option('-A', '--analyze-only', is_flag=True)
@click.option('-D', '--debug', is_flag=True)
@click.option('-v', '--verbose', is_flag=True)
@click.option('-f', '--force', is_flag=True)
@click.option('-k', '--keep', is_flag=True)
@click.option('-l', '--list', 'action', flag_value='list')
@click.option('-x', '--extract', 'action', flag_value='extract', default=True)
@click.argument('files', nargs=-1,
                type=click.Path(dir_okay=False, exists=True))
def uz(files, analyze_only, debug, verbose, action, keep, force):
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

        single_file = None
        if not nesting[-1].archive:
            single_file = get_filename(nesting, fn)
            info('resulting filename will be {!r}'.format(single_file))

        cmds = get_command(nesting, action, cmd_args, file.name)
        info('cmd: {}'.format(' | '.join(' '.join(args) for args in cmds)))

        if analyze_only:
            continue

        # implement the listing directly
        if not nesting[-1].archive and action == 'list':
            click.echo('{}'.format(single_file), err=True)
            continue

        if single_file:
            if os.path.exists(single_file) and not (force or click.confirm(
                '{} already exists, do you wish to overwrite?'
                .format(single_file)
            )):
                continue

        # repoen
        stdin = open(fn, 'rb')
        stdin.seek(0)
        while cmds:
            cmd = cmds.pop(0)

            if cmds:
                stdout = subprocess.PIPE
            elif single_file:
                stdout = open(single_file, 'wb')
                click.echo('extracting {}'.format(single_file), err=True)
            else:
                # just regular output here
                stdout = None

            if debug:
                click.echo('running {}'.format(' '.join(cmd)))
            proc = subprocess.Popen(cmd, stdin=stdin, stdout=stdout)
            stdin = proc.stdout

        # wait for extraction to complete
        proc.wait()
