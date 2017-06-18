import asyncio
import os.path
import ipaddress
from collections import namedtuple

import aiohttp
import maxminddb

from .utils import log, BASE_DIR


GeoData = namedtuple('GeoData', ['code', 'name'])
_mmdb_reader = maxminddb.open_database(
    os.path.join(BASE_DIR, 'data', 'GeoLite2-Country.mmdb'))


class Resolver(aiohttp.resolver.AsyncResolver):
    """Async host resolver based on aiodns."""

    _cached_hosts = {}

    def __init__(self, timeout=5, loop=None, *args, **kwargs):
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop()
        super().__init__(*args, loop=self._loop, **kwargs)

    @staticmethod
    def host_is_ip(host):
        """Check a host is IP address."""
        # TODO: add IPv6 support
        try:
            ipaddress.IPv4Address(host)
        except ipaddress.AddressValueError:
            return False
        else:
            return True

    @staticmethod
    def get_ip_info(ip):
        """Return geo information about IP address.

        `code` - ISO code
        `name` - The full name of the country proxy location
        """
        try:
            ipInfo = _mmdb_reader.get(ip) or {}
        except (maxminddb.errors.InvalidDatabaseError, ValueError):
            ipInfo = {}

        code, name = '--', 'Unknown'
        if 'country' in ipInfo:
            code = ipInfo['country']['iso_code']
            name = ipInfo['country']['names']['en']
        elif 'continent' in ipInfo:
            code = ipInfo['continent']['code']
            name = ipInfo['continent']['names']['en']
        return GeoData(code, name)

    async def get_real_ext_ip(self):
        """Return real external IP address."""
        try:
            with aiohttp.Timeout(self._timeout, loop=self._loop):
                async with aiohttp.ClientSession(loop=self._loop) as session,\
                        session.get('http://httpbin.org/ip') as resp:
                    data = await resp.json()
        except asyncio.TimeoutError as e:
            raise RuntimeError('Could not get a external IP. Error: %s' % e)
        else:
            ip = data['origin'].split(', ')[0]
            log.debug('Real external IP: %s' % ip)
        return ip
