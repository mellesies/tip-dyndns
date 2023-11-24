"""tipdyndns/cli.py"""
import logging

import click
import rich

import IPython
from traitlets.config.loader import Config
import pyfiglet
import textwrap


import transip

from . import config
from . import main
from . import util


log = logging.getLogger('tipdyndns')

def init(config_file, verbose, log_file):
    cfg = config.Configuration('tipdyndns')
    cfg.update(config_file)

    # Enable logging, overriding the console setting
    if verbose is not None:
        cfg.settings.logging.use_console = verbose

    if log_file is not None:
        cfg.settings.logging.file = log_file

    log_file = util.setup_logging(cfg)
    util.log_app_header('tipdyndns')
    log.debug(f"Logging to '{log_file}'")

    return cfg

@click.group()
@click.option('-c', '--config', 'config_file', default=None, type=click.Path(exists=True, dir_okay=False))
@click.option('-v', '--verbose', default=None, is_flag=True, show_default=True)
@click.option('-l', '--log', 'log_file', default=None, type=str)
@click.pass_context
def cli(ctx, config_file, verbose, log_file):
    cfg = init(config_file, verbose, log_file)

    ctx.ensure_object(dict)
    ctx.obj['cfg'] = cfg


@cli.command()
@click.pass_context
def dirs(ctx):
    """Print application directories."""
    cfg = ctx.obj['cfg']
    rich.print("Default directories:")
    rich.print(f" * Log dir: '{cfg.log_dir}'")
    rich.print(f" * Config dir: '{cfg.config_dir}'")
    rich.print(f" * Data dir: '{cfg.data_dir}'")


@cli.command()
@click.pass_context
def display_config(ctx):
    rich.print(ctx.obj['cfg'])


@cli.command()
@click.pass_context
def current_ip(ctx):
    """Return the current (external) ip adress"""
    cfg = ctx.obj['cfg']
    print(main.get_current_ip(cfg))


@cli.command()
@click.option('--reset', default=False, is_flag=True)
@click.pass_context
def run(ctx, reset):
    cfg = ctx.obj['cfg']
    main.run(cfg, reset)


@cli.command()
@click.option('-d', '--domain', default='zakbroek.com')
@click.pass_context
def check(ctx, domain):
    cfg = ctx.obj['cfg']
    client = main.get_transip_client(cfg)

    main.list_dns_entries_for_domain(client, domain)

# ------------------------------------------------------------------------------
# shell
# ------------------------------------------------------------------------------
@cli.command()
@click.option('--online/--offline', default=True, is_flag=True)
@click.pass_context
def shell(ctx, online):
    """Run a shell."""
    # Retrieve configuration from context
    cfg = ctx.obj['cfg']

    # Namespace for the shell
    namespace = {
        'main': main,
        'cfg': cfg,
        'tip': main.get_transip_client(cfg),
        'db': main.Database(cfg),
    }


    line = ''
    banner1 = line + pyfiglet.figlet_format('tipdyndns', font="graffiti")
    banner2 = textwrap.dedent(f"""

    The following variables/modules are available:
        {[n for n in namespace.keys()]}

    """)

    c = Config()
    c.TerminalInteractiveShell.banner1 = banner1
    c.TerminalInteractiveShell.banner2 = banner2

    IPython.start_ipython(
        argv=[],
        display_banner=True,
        config=c,
        user_ns=namespace
    )

