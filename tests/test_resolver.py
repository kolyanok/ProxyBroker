import socket
from unittest.mock import Mock, patch

import aiodns

from .utils import AsyncTestCase, ResolveResult, future_iter
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
            resp.json.side_effect = resp.release.side_effect = _side_effect
            return resp

        with patch("aiohttp.client.ClientSession._request") as resp:
            resp.side_effect = side_effect
            self.assertEqual(await rs.get_real_ext_ip(), '127.0.0.1')

    async def test_resolve(self):
        rs = Resolver(timeout=0.1)
        hinfo = await rs.resolve('127.0.0.1')
        host = hinfo[0]['host']
        self.assertEqual(host, '127.0.0.1')

        with self.assertRaises(aiodns.error.DNSError):
            await rs.resolve('256.0.0.1')

        with patch("aiodns.DNSResolver.gethostbyname") as query:
            query.side_effect = future_iter(ResolveResult(['127.0.0.1'], 0))
            hinfo = await rs.resolve('test.com')
            host = hinfo[0]['host']
            self.assertEqual(host, '127.0.0.1')

    async def test_resolve_family(self):
        rs = Resolver(timeout=0.1)
        with patch("aiodns.DNSResolver.gethostbyname") as query:
            query.side_effect = future_iter(ResolveResult(['127.0.0.2'], 0))
            hinfo = await rs.resolve('test2.com', family=socket.AF_INET)
            resp = [{'hostname': 'test2.com', 'host': '127.0.0.2', 'port': 0,
                     'family': socket.AF_INET, 'proto': socket.IPPROTO_IP,
                     'flags': socket.AI_NUMERICHOST}]
            self.assertEqual(hinfo, resp)
