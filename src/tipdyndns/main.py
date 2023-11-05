"""Main functionality."""
import os
import logging
from transip import TransIP

from . import util
from .hg659client import HG659Client

IP_HISTORY_FILENAME = 'ip_history.yaml'

log = logging.getLogger('tipdyndns')

def run(cfg, reset):
    """Check the current (external) IP address and update the DNS server"""
    # Get the current (external IP address)
    current_ip = get_current_ip(cfg)

    log.debug(f"Current IP: '{current_ip}'")

    # Get the IP history
    ip_hist_file = os.path.join(cfg.data_dir, IP_HISTORY_FILENAME)

    if reset:
        ip_history = []
    else:
        ip_history = util.load_yaml(ip_hist_file)

    # Get the last known IP from config
    if ip_history:
        last_ip = ip_history[-1]
    else:
        last_ip = ''

    log.debug(f"Last known IP: '{last_ip}'")


    if current_ip != last_ip:
        log.info(f"IP address has changed!")

        # Update TransIP hosts ...
        client = get_transip_client(cfg)

        for host in cfg.settings.hosts:
            log.info(f"Updating '{host}'")
            name, domain = host.split('.', 1)
            dns_entry = get_dns_entry_by_name(client, domain, name)

            if dns_entry is None:
                # Create new entry
                log.info("Creating new DNS entry!")

                add_dns_entry(
                    client,
                    domain,
                    name,
                    cfg.settings.expire,
                    'A',
                    current_ip,
                )
            else:
                log.info("Updating DNS entry!")
                update_dns_entry(client, domain, dns_entry, current_ip)

        # All done updating TransIP
        log.debug("Updating IP History")

        # Add the new IP to history
        ip_history.append(current_ip)

        # Store the updated IP
        # util.save_yaml(ip_history, ip_hist_file)



def get_current_ip(cfg) -> str:
    """Return the current (external) IP address."""
    m = cfg.settings.modem
    client = HG659Client(m.host, m.username, m.password)

    return client.get_current_ip()

def get_transip_client(cfg) -> TransIP:
    """Create a TransIP Client."""
    client = TransIP(
        login=cfg.settings.transip.username,
        private_key=cfg.settings.transip.privkey,
        global_key=True
    )

    return client

def list_dns_entries_for_domain(client, domain):
    """Print all entries for a domain to the console."""
    # Retrieve a domain by its name.
    d = client.domains.get(domain)

    # Retrieve the DNS records of a single domain.
    records = d.dns.list()

    # Show the DNS record information on the screen.
    for record in records:
        print(f"DNS: {record.name} {record.expire} {record.type} {record.content}")


def add_dns_entry(
    client: HG659Client, domain: str, name: str, exp: int,
    type_: str, content: str
):
    d = client.domains.get(domain)
    d.dns.create({
        'name': name,
        'expire': exp,
        'type': type_,
        'content': content,
    })

def update_dns_entry(client, domain, entry, content):
    d = client.domains.get(domain)
    d.dns.update({
        'name': entry.name,
        'expire': entry.expire,
        'type': entry.type,
        'content': content,
    })


def get_dns_entry_by_name(client: HG659Client, domain: str, name: str):
    # Retrieve a domain by its name.
    d = client.domains.get(domain)

    # Retrieve the DNS records of a single domain.
    records = d.dns.list()

    # Show the DNS record information on the screen.
    for record in records:
        if record.name == name:
            return record