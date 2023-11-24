"""Main functionality."""
from typing import List
import os
import logging
from requests import get
from datetime import datetime

import duckdb
from transip import TransIP

from . import util

log = logging.getLogger('tipdyndns')


class Database(object):

    def __init__(self, cfg, reset=False):
        filename = os.path.join(cfg.data_dir, cfg.settings.database)
        conn = duckdb.connect(filename)

        try:
            conn.sql("CREATE TABLE ip_history (id INTEGER, ip VARCHAR, assigned_dt DATETIME)")
            conn.sql("CREATE SEQUENCE seq_ip_history_id START 1;")
        except duckdb.CatalogException:
            pass

        if reset:
            conn.sql("DELETE FROM ip_history")

        self.conn = conn

    def get_entries(self):
        return self.conn.sql("select * from ip_history").fetchall()

    def get_latest_entry(self):

        return self.conn.sql("""
            select
                ip,
                assigned_dt
            from
                ip_history
            inner join (
                select
                    max(assigned_dt) as timestamp
                from
                    ip_history
            ) as newest
            on ip_history.assigned_dt == newest.timestamp
        """).fetchone()

    def add_entry(self, ip_address, assigned_at=None):
        if assigned_at is None:
            assigned_at = datetime.now()

        self.conn.sql(f"""
            insert into ip_history values(
                nextval('seq_ip_history_id'),
                '{ip_address}',
                '{assigned_at}',
            )
        """)


def create_or_update_host_record(transip_client, host, current_ip, expire):
    """Create or update a host record at TransIP."""

    # First get the currenct record.
    log.info(f"Checking '{host}'")
    hostname, domain = host.split('.', 1)
    dns_entry = get_dns_entry_by_name(transip_client, domain, hostname)

    if dns_entry is None:
        log.info("Creating new DNS entry!")
        create_dns_entry(
            transip_client,
            domain,
            hostname,
            expire,
            'A',
            current_ip,
        )

    else:
        log.info("Updating DNS entry!")
        update_dns_entry(transip_client, domain, dns_entry, current_ip)

def run(cfg, reset):
    """Check the current (external) IP address and update the DNS server"""
    # Get the current (external IP address)
    current_ip = get_current_ip(cfg)

    log.debug(f"Current IP: '{current_ip}'")

    # Get the IP history
    db = Database(cfg, reset)

    # Get the last known IP from config
    latest_entry = db.get_latest_entry()

    try:
        last_ip = latest_entry[0]
    except:
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

                create_dns_entry(
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
        db.add_entry(current_ip)



def get_current_ip(cfg) -> str:
    """Return the current (external) IP address."""
    return get('https://api.ipify.org').text

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

def create_dns_entry(
    client: TransIP, domain: str, name: str, exp: int,
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

def get_dns_entry_by_name(client: TransIP, domain: str, name: str):
    # Retrieve a domain by its name.
    d = client.domains.get(domain)

    # Retrieve the DNS records of a single domain.
    records = d.dns.list()

    # Show the DNS record information on the screen.
    for record in records:
        if record.name == name  and record.type == 'A':
            return record