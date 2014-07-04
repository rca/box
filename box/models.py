import json

BASE_URL = 'https://api.box.com/2.0'

FOLDERS_URL = '{}/folders'.format(BASE_URL)
FOLDER_LIST_URL = '{}/{{}}/items'.format(FOLDERS_URL)

UPLOAD_BASE_URL = 'https://upload.box.com/api/2.0'
UPLOAD_FILE_URL = '{}/files/content'.format(UPLOAD_BASE_URL)

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

        This will throw a 409 HTTP error when the file already exits

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

        response = self.provider_logic.post(UPLOAD_FILE_URL, data=data, files=files)

        return response.json()
