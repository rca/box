import mock
import unittest

from box import Client


class ClientTestCase(unittest.TestCase):
    def setUp(self):
        self.provider = mock.Mock()
        self.client = Client(self.provider)

    @mock.patch('box.models.ProviderLogic.get')
    def test_folders(self, get_mock):
        """
        Ensures only one item is returned even though the limit is 100 by default
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 1, 'entries': ['folder']}

        get_mock.return_value = response

        folders = list(self.client.folders())

        self.assertEqual(['folder'], folders)

    @mock.patch('box.models.ProviderLogic.get')
    def test_folders_inner_limit(self, get_mock):
        """
        Ensures the limit is honored even if an upstream result contains more items
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 100, 'entries': ['folder'] * 100}

        get_mock.return_value = response

        folders = list(self.client.folders(limit=10))

        self.assertEqual(['folder']*10, folders)

    @mock.patch('box.models.ProviderLogic.get')
    def test_folders_outer_limit(self, get_mock):
        """
        Ensures multiple requests are made to honor the outer limit
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 300, 'entries': ['folder'] * 100}

        get_mock.return_value = response

        folders = list(self.client.folders(limit=200))

        self.assertEqual(['folder']*200, folders)

    @mock.patch('box.models.ProviderLogic.get')
    def test_folders_parent_id(self, get_mock):
        """
        Ensures only one item is returned even though the limit is 100 by default
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 300, 'entries': ['folder'] * 100}

        get_mock.return_value = response

        folders = list(self.client.folders(parent={'id': 123}))

        self.assertEqual(['folder']*100, folders)

        get_mock.assert_called_with(
            'https://api.box.com/2.0/folders/123/items',
            params={'limit': 100, 'offset': 0}
        )
