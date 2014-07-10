import functools
import json
import mock
import unittest

from requests.exceptions import HTTPError

from box import Client
from box.models import FILE_URL, FOLDER_URL, FOLDERS_URL, UPDATE_FILE_URL, UPLOAD_FILE_URL


class ClientTestCase(unittest.TestCase):
    def setUp(self):
        self.oauth2_client = mock.Mock()
        self.client = Client(self.oauth2_client)

    def test_add_tags(self):
        item = {'id': 1234}
        tags = ['foo']
        added_tags = ['bar']

        self.client.get_tags = mock.Mock()
        self.client.get_tags.return_value = tags[:]  # make a copy of the list

        new_tags = self.client.add_tags(item, added_tags)
        expected_tags = tags + added_tags

        self.assertEqual(expected_tags, new_tags)

        url = FILE_URL.format(item['id'])

        self.oauth2_client.put.assert_called_with(url, data=json.dumps({'tags': expected_tags}))

    def test_add_tags_none_added(self):
        item = {'id': 1234}
        tags = ['foo']
        added_tags = ['bar']
        expected_tags = tags + added_tags

        self.client.get_tags = mock.Mock()
        self.client.get_tags.return_value = expected_tags

        new_tags = self.client.add_tags(item, added_tags)

        self.assertEqual(expected_tags, new_tags)

        self.assertEqual(False, self.oauth2_client.put.called)

    def test_create_folder(self):
        name = 'foo'
        parent = {'id': 0, 'name': 'root'}

        expected = {'status': 'ok'}
        self.oauth2_client.post().json.return_value = expected

        json_data = self.client.create_folder(name, parent=parent)

        payload = json.dumps({'name': name, 'parent': {'id': parent['id']}})
        self.oauth2_client.post.assert_called_with(FOLDERS_URL, data=payload)

        self.assertEqual(expected, json_data)

    def test_delete(self):
        file_id = 123
        self.client.delete({'id': file_id, 'etag': 1})

        url = FILE_URL.format(file_id)
        self.oauth2_client.delete.assert_called_with(url, headers={'If-Match': 1})

    def test_delete_folder(self):
        folder_id = 123
        self.client.delete_folder({'id': folder_id})

        url = FOLDER_URL.format(folder_id)
        self.oauth2_client.delete.assert_called_with(url, params={'recursive': False})

    def test_delete_folder_recursive(self):
        folder_id = 123
        self.client.delete_folder({'id': folder_id}, recursive=True)

        url = FOLDER_URL.format(folder_id)
        self.oauth2_client.delete.assert_called_with(url, params={'recursive': True})

    def test_file_info(self):
        item = {'id': 1234}
        url = FILE_URL.format(item['id'])

        expected = {}
        self.oauth2_client.get.return_value.json.return_value = expected

        info = self.client.file_info(item)

        self.oauth2_client.get.assert_called_with(url, params={})

        self.assertEqual(expected, info)

    def test_file_info_with_fields(self):
        item = {'id': 1234}
        url = FILE_URL.format(item['id'])

        expected = {}
        self.oauth2_client.get.return_value.json.return_value = expected

        info = self.client.file_info(item, fields='tags')

        self.oauth2_client.get.assert_called_with(url, params={'fields': 'tags'})

        self.assertEqual(expected, info)

    def test_folders(self):
        """
        Ensures only one item is returned even though the limit is 100 by default
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 1, 'entries': ['folder']}

        self.oauth2_client.get.return_value = response

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

        response.json.side_effect = functools.partial(get_json, self.oauth2_client.get)

        self.oauth2_client.get.return_value = response

        folders = list(self.client.folder_items(limit=10))

        self.assertEqual(['folder']*10, folders)

    def test_get_etag(self):
        item = {'id': 1234}
        expected = 'etag'

        self.oauth2_client.get.return_value.json.return_value = {'etag': expected}

        etag = self.client.get_etag(item)

        self.assertEqual(expected, etag)

    def test_get_tags(self):
        item = {'id': 1234}
        expected = ['foo', 'bar']

        self.oauth2_client.get.return_value.json.return_value = {'tags': expected}

        tags = self.client.get_tags(item)

        self.assertEqual(expected, tags)

    def test_remove_tags(self):
        item = {'id': 1234}
        tags = ['foo']
        removed_tags = ['bar']

        self.client.get_tags = mock.Mock()
        self.client.get_tags.return_value = tags + removed_tags

        new_tags = self.client.remove_tags(item, removed_tags)

        self.assertEqual(tags, new_tags)

        url = FILE_URL.format(item['id'])

        self.oauth2_client.put.assert_called_with(url, data=json.dumps({'tags': tags}))

    def test_remove_tags_none_removed(self):
        item = {'id': 1234}
        tags = ['foo']
        removed_tags = ['bar']

        self.client.get_tags = mock.Mock()
        self.client.get_tags.return_value = tags

        new_tags = self.client.remove_tags(item, removed_tags)

        self.assertEqual(tags, new_tags)
        self.assertEqual(False, self.oauth2_client.put.called)

    def test_total_count(self):
        """
        Make sure additional requests aren't made when total_count is hit
        """
        response = mock.Mock()

        def get_json(get_mock, total_count=1):
            _args, _kwargs = get_mock.call_args
            num_folders = min(_kwargs['params']['limit'], total_count)
            return {'total_count': total_count, 'entries': ['folder'] * num_folders}

        response.json.side_effect = functools.partial(get_json, self.oauth2_client.get)

        self.oauth2_client.get.return_value = response

        # wrap in list() call in order for the debugger step into folder_items(),
        # i.e., the generator has to be evaluated.
        list(self.client.folder_items(limit=10))

        self.assertEqual(1, self.oauth2_client.get.call_count)

    def test_folders_outer_limit(self):
        """
        Ensures multiple requests are made to honor the outer limit
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 300, 'entries': ['folder'] * 100}

        self.oauth2_client.get.return_value = response

        folders = list(self.client.folder_items(limit=200))

        self.assertEqual(['folder']*200, folders)

    def test_folders_parent_id(self):
        """
        Ensures only one item is returned even though the limit is 100 by default
        """
        response = mock.Mock()
        response.json.return_value = {'total_count': 300, 'entries': ['folder'] * 100}

        self.oauth2_client.get.return_value = response

        folders = list(self.client.folder_items(parent={'id': 123}))

        self.assertEqual(['folder']*100, folders)

        self.oauth2_client.get.assert_called_with(
            'https://api.box.com/2.0/folders/123/items',
            params={'limit': 100, 'offset': 0}
        )

    def test_set_tags(self):
        item = {'id': 123}
        tags = ['foo']

        url = FILE_URL.format(item['id'])
        params = {'fields': 'tags'}
        data = json.dumps({'tags': tags})

        self.client.set_tags(item, tags)

        self.oauth2_client.put.assert_called_with(url, data=data)

    def test_update(self):
        item = {'id': 1234}

        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        self.client.update(item, fileobj, etag='etag')

        url = UPDATE_FILE_URL.format(item['id'])

        self.oauth2_client.post.assert_called_with(
            url,
            files={'filename': (fileobj.name, fileobj)},
            headers={'If-Match': 'etag'}
        )

    def test_update_etag_none(self):
        item = {'id': 1234}

        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        self.client.file_info = mock.Mock()
        self.client.file_info.return_value = {'etag': 'et'}

        self.client.update(item, fileobj)

        self.client.file_info.assert_called_with(item, fields='etag')

        url = UPDATE_FILE_URL.format(item['id'])
        self.oauth2_client.post.assert_called_with(
            url,
            files={'filename': (fileobj.name, fileobj)},
            headers={'If-Match': 'et'}
        )

    def test_update_with_hash(self):
        item = {'id': 1234}

        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        self.client.update(item, fileobj, etag='etag', content_hash='hash')

        url = UPDATE_FILE_URL.format(item['id'])

        self.oauth2_client.post.assert_called_with(
            url,
            files={'filename': (fileobj.name, fileobj)},
            headers={
                'Content-MD5': 'hash',
                'If-Match': 'etag',
            },
        )

    def test_update_file_info(self):
        expected = {'return': 'value'}
        self.oauth2_client.put.return_value.json.return_value = expected

        etag = 'etag'
        item = {'id': 1234}
        info = {'name': 'foo'}

        self.client.file_info = mock.Mock()
        self.client.file_info.return_value = {'etag': etag}

        response_json = self.client.update_file_info(item, info)

        url = FILE_URL.format(item['id'])

        self.oauth2_client.put.assert_called_with(
            url, data=json.dumps(info), headers={'If-Match': etag})

        self.assertEqual(expected, response_json)

    def test_update_folder_info(self):
        expected = {'return': 'value'}
        self.oauth2_client.put.return_value.json.return_value = expected

        etag = 'etag'
        item = {'id': 1234}
        info = {'name': 'foo'}

        self.client.folder_info = mock.Mock()
        self.client.folder_info.return_value = {'etag': etag}

        response_json = self.client.update_folder_info(item, info)

        url = FOLDER_URL.format(item['id'])

        self.oauth2_client.put.assert_called_with(
            url, data=json.dumps(info), headers={'If-Match': etag})

        self.assertEqual(expected, response_json)

    def test_upload(self):
        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        parent = {'id': 0}

        expected = {'status': 'ok'}
        self.oauth2_client.post.return_value.json.return_value = expected

        response_json = self.client.upload(parent, fileobj)

        self.oauth2_client.post.assert_called_with(
            UPLOAD_FILE_URL,
            data={'parent_id': parent['id']},
            files={'filename': (fileobj.name, fileobj)},
            headers={},
        )

        self.assertEqual(expected, response_json)

    def test_upload_with_hash(self):
        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        parent = {'id': 0}

        expected = {'status': 'ok'}
        self.oauth2_client.post.return_value.json.return_value = expected

        response_json = self.client.upload(parent, fileobj, content_hash='hash')

        self.oauth2_client.post.assert_called_with(
            UPLOAD_FILE_URL,
            data={'parent_id': parent['id']},
            files={'filename': (fileobj.name, fileobj)},
            headers={'Content-MD5': 'hash'},
        )

        self.assertEqual(expected, response_json)

    def test_upload_existing_file(self):
        fileobj = mock.Mock()

        parent = {'id': 0}

        # setup POST to have two responses
        self.oauth2_client.post.side_effect = [HTTPError]

        self.assertRaises(HTTPError, self.client.upload, parent, fileobj)

    def test_upload_or_update(self):
        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        parent = {'id': 0}

        expected = {'status': 'ok'}
        self.oauth2_client.post.return_value.json.return_value = expected

        response_json, uploaded = self.client.upload_or_update(parent, fileobj)

        self.oauth2_client.post.assert_called_with(
            UPLOAD_FILE_URL,
            data={'parent_id': parent['id']},
            files={'filename': (fileobj.name, fileobj)},
            headers={},
        )

        self.assertEqual(expected, response_json)
        self.assertEqual(True, uploaded)

    def test_upload_or_update_with_hash(self):
        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        parent = {'id': 0}

        expected = {'status': 'ok'}
        self.oauth2_client.post.return_value.json.return_value = expected

        response_json, uploaded = self.client.upload_or_update(parent, fileobj, content_hash='hash')

        self.oauth2_client.post.assert_called_with(
            UPLOAD_FILE_URL,
            data={'parent_id': parent['id']},
            files={'filename': (fileobj.name, fileobj)},
            headers={'Content-MD5': 'hash'},
        )

        self.assertEqual(expected, response_json)
        self.assertEqual(True, uploaded)

    def test_upload_or_update_existing_file(self):
        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        parent = {'id': 0}

        error_response_mock = mock.Mock(status_code=409)
        error_json = {'context_info': {'conflicts': {'id': 1234, 'etag': 'etag'}}}
        error_response_mock.json.return_value = error_json
        error = HTTPError(response=error_response_mock)

        expected = {'status': 'ok'}
        response = mock.Mock()
        response.json.return_value = expected

        # setup POST to have two responses
        self.oauth2_client.post.side_effect = [error, response]

        response_json, uploaded = self.client.upload_or_update(parent, fileobj)

        self.oauth2_client.post.assert_called_with(
            UPDATE_FILE_URL.format(error_json['context_info']['conflicts']['id']),
            headers={'If-Match': error_json['context_info']['conflicts']['etag']},
            files={'filename': (fileobj.name, fileobj)}
        )

        self.assertEqual(expected, response_json)
        self.assertEqual(False, uploaded)

    def test_upload_or_update_existing_file_with_hash(self):
        fileobj = mock.Mock()
        fileobj.name = 'foo.txt'

        parent = {'id': 0}

        error_response_mock = mock.Mock(status_code=409)
        error_json = {'context_info': {'conflicts': {'id': 1234, 'etag': 'etag'}}}
        error_response_mock.json.return_value = error_json
        error = HTTPError(response=error_response_mock)

        expected = {'status': 'ok'}
        response = mock.Mock()
        response.json.return_value = expected

        self.oauth2_client.post.side_effect = [error, response]

        response_json, uploaded = self.client.upload_or_update(parent, fileobj, content_hash='hash')

        self.oauth2_client.post.assert_called_with(
            UPDATE_FILE_URL.format(error_json['context_info']['conflicts']['id']),
            headers={
                'If-Match': error_json['context_info']['conflicts']['etag'],
                'Content-MD5': 'hash',
            },
            files={'filename': (fileobj.name, fileobj)}
        )

        self.assertEqual(expected, response_json)
        self.assertEqual(False, uploaded)
