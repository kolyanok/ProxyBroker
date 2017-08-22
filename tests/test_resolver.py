import socket
from unittest.mock import Mock, patch

import aiodns
import aiohttp

from .utils import AsyncTestCase
from proxybroker.resolver import Resolver


class TestResolver(AsyncTestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_host_is_ip(self):
        rs = Resolver(timeout=0.1)
        self.assertTrue(rs.host_is_ip('127.0.0.1'))
        self.assertFalse(rs.host_is_ip('256.0.0.1'))
        self.assertFalse(rs.host_is_ip('test.com'))

    def test_get_ip_info(self):
        rs = Resolver(timeout=0.1)
        self.assertEqual(rs.get_ip_info('test.com'), ('--', 'Unknown'))
        self.assertEqual(rs.get_ip_info('127.0.0.1'), ('--', 'Unknown'))
        self.assertEqual(rs.get_ip_info('8.8.8.8'), ('US', 'United States'))

    async def test_get_real_ext_ip(self):
        rs = Resolver(timeout=0.1)

        async def side_effect(*args, **kwargs):
            async def _side_effect(*args, **kwargs):
                return {'origin': '127.0.0.1'}
            resp = Mock()
            resp.json.side_effect = _side_effect
            return resp

        with patch("aiohttp.client.ClientSession._request") as resp:
            resp.side_effect = side_effect
            self.assertEqual(await rs.get_real_ext_ip(), '127.0.0.1')

    async def test_resolve(self):
        async def _side_effect(*args, **kwargs):
            host = 'test.com'
            address = '127.0.0.1'
            port = 80
            family = socket.AF_INET
            resolve_result = [{'hostname': host,
                               'host': address, 'port': port,
                               'family': family, 'proto': 0,
                               'flags': socket.AI_NUMERICHOST}]
            return resolve_result

        rs = Resolver(timeout=0.1)
        hinfo = await rs.resolve('127.0.0.1')
        host = hinfo[0]['host']
        self.assertEqual(host, '127.0.0.1')

        if isinstance(rs, aiohttp.resolver.ThreadedResolver):
            with self.assertRaises(socket.gaierror):
                await rs.resolve('256.0.0.1')
        if isinstance(rs, aiohttp.resolver.AsyncResolver):
            with self.assertRaises(aiodns.error.DNSError):
                await rs.resolve('256.0.0.1')

        with patch("aiohttp.DefaultResolver.resolve") as query:
            query.side_effect = _side_effect
            hinfo = await rs.resolve('test.com')
            host = hinfo[0]['host']
            self.assertEqual(host, '127.0.0.1')

    async def test_resolve_family(self):
        async def _side_effect(*args, **kwargs):
            host = 'test2.com'
            address = '127.0.0.2'
            port = 0
            family = socket.AF_INET
            resolve_result = [{'hostname': host,
                               'host': address, 'port': port,
                               'family': family, 'proto': socket.IPPROTO_IP,
                               'flags': socket.AI_NUMERICHOST}]
            return resolve_result

        rs = Resolver(timeout=0.1)
        with patch("aiohttp.DefaultResolver.resolve") as query:
            query.side_effect = _side_effect
            hinfo = await rs.resolve('test2.com', family=socket.AF_INET)

            resp = [{'hostname': 'test2.com', 'host': '127.0.0.2', 'port': 0,
                     'family': socket.AF_INET, 'proto': socket.IPPROTO_IP,
                     'flags': socket.AI_NUMERICHOST}]
            self.assertEqual(hinfo, resp)
