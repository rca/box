import functools
import json
import mock
import unittest

from box import Client
from box.models import FOLDERS_URL, UPLOAD_FILE_URL


class ClientTestCase(unittest.TestCase):
    def setUp(self):
        self.provider_logic = mock.Mock()
        self.client = Client(self.provider_logic)

    def test_create_folder(self):
        name = 'foo'
        parent = {'id': 0, 'name': 'root'}

        expected = {'status': 'ok'}
        self.provider_logic.post().json.return_value = expected

        json_data = self.client.create_folder(name, parent=parent)

        payload = json.dumps({'name': name, 'parent': {'id': parent['id']}})
        self.provider_logic.post.assert_called_with(FOLDERS_URL, data=payload)

        self.assertEqual(expected, json_data)

    def test_folders(self):
        """
        Ensures only one item is returned even though the limit is 100 by default
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 1, 'entries': ['folder']}

        self.provider_logic.get.return_value = response

        folders = list(self.client.folder_items())

        self.assertEqual(['folder'], folders)

    def test_folders_inner_limit(self):
        """
        Ensures the limit is honored even if an upstream result contains more items
        """
        response = mock.Mock()

        def get_json(get_mock):
            _args, _kwargs = get_mock.call_args
            return {'total_count': 100, 'entries': ['folder'] * _kwargs['params']['limit']}

        response.json.side_effect = functools.partial(get_json, self.provider_logic.get)

        self.provider_logic.get.return_value = response

        folders = list(self.client.folder_items(limit=10))

        self.assertEqual(['folder']*10, folders)

    def test_total_count(self):
        """
        Make sure additional requests aren't made when total_count is hit
        """
        response = mock.Mock()

        def get_json(get_mock, total_count=1):
            _args, _kwargs = get_mock.call_args
            num_folders = min(_kwargs['params']['limit'], total_count)
            return {'total_count': total_count, 'entries': ['folder'] * num_folders}

        response.json.side_effect = functools.partial(get_json, self.provider_logic.get)

        self.provider_logic.get.return_value = response

        # wrap in list() call in order for the debugger step into folder_items(),
        # i.e., the generator has to be evaluated.
        list(self.client.folder_items(limit=10))

        self.assertEqual(1, self.provider_logic.get.call_count)

    def test_folders_outer_limit(self):
        """
        Ensures multiple requests are made to honor the outer limit
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 300, 'entries': ['folder'] * 100}

        self.provider_logic.get.return_value = response

        folders = list(self.client.folder_items(limit=200))

        self.assertEqual(['folder']*200, folders)

    def test_folders_parent_id(self):
        """
        Ensures only one item is returned even though the limit is 100 by default
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 300, 'entries': ['folder'] * 100}

        self.provider_logic.get.return_value = response

        folders = list(self.client.folder_items(parent={'id': 123}))

        self.assertEqual(['folder']*100, folders)

        self.provider_logic.get.assert_called_with(
            'https://api.box.com/2.0/folders/123/items',
            params={'limit': 100, 'offset': 0}
        )

    def test_upload(self):
        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        parent = {'id': 0}

        expected = {'status': 'ok'}
        self.provider_logic.post.return_value.json.return_value = expected

        response_json = self.client.upload(parent, fileobj)

        self.provider_logic.post.assert_called_with(
            UPLOAD_FILE_URL,
            data={'parent_id': parent['id']},
            files={'filename': (fileobj.name, fileobj)}
        )

        self.assertEqual(expected, response_json)
