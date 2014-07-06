import json

from requests.exceptions import HTTPError

BASE_URL = 'https://api.box.com/2.0'

FILE_URL = '{}/files/{{}}'.format(BASE_URL)

FOLDERS_URL = '{}/folders'.format(BASE_URL)
FOLDER_URL = '{}/{{}}'.format(FOLDERS_URL)
FOLDER_LIST_URL = '{}/items'.format(FOLDER_URL)

UPLOAD_BASE_URL = 'https://upload.box.com/api/2.0'
UPLOAD_FILE_URL = '{}/files/content'.format(UPLOAD_BASE_URL)

UPDATE_FILE_URL = '{}/files/{{}}/content'.format(UPLOAD_BASE_URL)

MAX_FOLDERS = 1000


class Client(object):
    def __init__(self, provider_logic):
        """
        Box client constructor
        :param provider_logic: oauthclient ProviderLogic instance
        :return:
        """
        self.provider_logic = provider_logic

    def create_folder(self, name, parent):
        """
        Creates a folder within the given parent

        :param name: The name of the folder to create
        :param parent: Box API folder item dictionary
        :return: The Box API response JSON data
        """
        payload = json.dumps({
            'name': name,
            'parent': {
                'id': parent['id'],
            }
        })

        response = self.provider_logic.post(FOLDERS_URL, data=payload)

        return response.json()

    def delete(self, item):
        """
        Deletes a file

        :param item: Box API dictionary representing the item to delete
        :return: None
        """
        url = FILE_URL.format(item['id'])
        headers = {
            'If-Match': item['etag']
        }

        self.provider_logic.delete(url, headers=headers)

    def delete_folder(self, item, recursive=False):
        """
        Deletes a folder

        :param item: Box API dictionary representing the folder to delete
        :param recursive: Whether to delete a folder that contains items.  Default=False
        :return: None
        """
        folder_id = item['id']
        url = FOLDER_URL.format(folder_id)

        params = {
            'recursive': recursive,
        }

        self.provider_logic.delete(url, params=params)

    def folder_items(self, parent=None, limit=100, offset=0):
        """
        Generator for items in given parent
        :param parent: optionarl Box API folder item dictionary
        :param limit: How many items to retrieve
        :param offset: Item offset
        :return: Generator of Box API item dictionaries
        """
        if parent:
            folder_id = parent['id']
        else:
            folder_id = 0

        url = FOLDER_LIST_URL.format(folder_id)

        count = 0
        while count < limit:
            _limit = min(MAX_FOLDERS, limit-count)
            params = {
                'limit': _limit,
                'offset': offset+count,
            }

            response = self.provider_logic.get(url, params=params)
            response.raise_for_status()

            json_data = response.json()

            # determine how many more entries to get from the result set
            entries = json_data['entries']
            for entry in entries:
                yield entry

            # increment the count by the number of entries
            count += len(entries)

            # if we hit the total number of entries, we have to be done
            total_count = json_data['total_count']
            if count >= total_count:
                break

    def upload(self, parent, fileobj):
        """
        Upload a file to the given parent

        This handles 409 HTTP errors and will attempt to update the existing file.

        :param parent: box item dictionary representing the parent folder to upload to
        :param fileobj: a file-like object to get the contents from
        :return: Box API response JSON data
        """
        data = {
            'parent_id': parent['id'],
        }

        files = {
            'filename': (fileobj.name, fileobj),
        }

        try:
            response = self.provider_logic.post(UPLOAD_FILE_URL, data=data, files=files)
        except HTTPError, exc:
            if exc.response.status_code != 409:
                raise

            error_json = exc.response.json()
            existing_file_id = error_json['context_info']['conflicts']['id']
            existing_file_etag = error_json['context_info']['conflicts']['etag']

            # update the file instead of upload it
            fileobj.seek(0, 0)  # rewind the file just in case.

            headers = {
                'If-Match': existing_file_etag,
            }

            url = UPDATE_FILE_URL.format(existing_file_id)
            response = self.provider_logic.post(url, files=files, headers=headers)

        return response.json()
