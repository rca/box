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

ROOT_FOLDER = {'id': 0}


class Client(object):
    def __init__(self, oauth2_client):
        """
        Box client constructor
        :param oauth2_client: OAuth2Client instance
        :return:
        """
        self.oauth2_client = oauth2_client

    def add_tags(self, item, tags):
        """
        Adds tags to the given item

        :param item: Box API item dictionary
        :param tags: List of tags to add to the item
        :return: New list of tags
        """
        current_tags = self.get_tags(item)

        update = False
        for tag in tags:
            if tag not in current_tags:
                update = True
                current_tags.append(tag)

        if update:
            self.set_tags(item, current_tags)

        return current_tags

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

        response = self.oauth2_client.post(FOLDERS_URL, data=payload)

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

        self.oauth2_client.delete(url, headers=headers)

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

        self.oauth2_client.delete(url, params=params)

    def file_info(self, item, fields=None):
        """
        Returns file information for the given item

        :param item: Box API item dictionary
        :return:
        """
        url = FILE_URL.format(item['id'])

        params = {}

        if fields:
            params['fields'] = fields

        return self.oauth2_client.get(url, params=params).json()

    def folder_items(self, parent=None, limit=100, offset=0):
        """
        Generator for items in given parent
        :param parent: optionarl Box API folder item dictionary
        :param limit: How many items to retrieve
        :param offset: Item offset
        :return: Generator of Box API item dictionaries
        """
        if parent is None:
            parent = ROOT_FOLDER

        url = FOLDER_LIST_URL.format(parent['id'])

        count = 0
        while count < limit:
            _limit = min(MAX_FOLDERS, limit-count)
            params = {
                'limit': _limit,
                'offset': offset+count,
            }

            response = self.oauth2_client.get(url, params=params)
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

    def get_etag(self, item):
        return self.file_info(item, fields='etag')['etag']

    def get_tags(self, item):
        return self.file_info(item, fields='tags')['tags']

    def remove_tags(self, item, tags):
        """
        Removes tags from the given item

        :param item: Box API item dictionary
        :param tags: List of tags to remove from the item
        :return: New list of tags
        """
        current_tags = self.get_tags(item)

        update = False
        new_tags = []
        for tag in current_tags:
            if tag in tags:
                update = True
                continue

            new_tags.append(tag)

        if update:
            self.set_tags(item, new_tags)

        return new_tags

    def set_tags(self, item, tags):
        """
        Sets the tags for the given item

        :param item: Box API item dictionary
        :param tags: List of tags
        :return:
        """
        url = FILE_URL.format(item['id'])

        params = {
            'fields': 'tags',
        }

        data = json.dumps({
            'tags': tags,
        })

        self.oauth2_client.put(url, data=data)

    def update(self, item, fileobj, etag=None, content_hash=None):
        headers = {
            'If-Match': etag or self.get_etag(item),
        }

        if content_hash:
            headers.update({
                'Content-MD5': content_hash,
            })

        files = {
            'filename': (fileobj.name, fileobj),
        }

        url = UPDATE_FILE_URL.format(item['id'])

        response = self.oauth2_client.post(url, files=files, headers=headers)
        response.raise_for_status()

        return response.json()

    def update_info(self, item, info):
        """
        Updates the given item's metadata, such as name, description, etc.

        :param item: Box API item dictionary
        :param info: dictionary of information to modify
        :return: Box API item dictionary
        """
        url = FILE_URL.format(item['id'])
        payload = json.dumps(info)

        response = self.oauth2_client.put(url, data=payload)

        return response.json()

    def upload(self, parent, fileobj, content_hash=None):
        """
        Upload a file to the given parent

        An optional content_hash can be passed in.  When given, the request is
        made with the `Content-MD5` header.

        :param parent: box item dictionary representing the parent folder to upload to
        :param fileobj: a file-like object to get the contents from
        :param content_hash: Optional, the file's SHA-1 hash.
        :return: Box API response JSON data
        """
        data = {
            'parent_id': parent['id'],
        }

        files = {
            'filename': (fileobj.name, fileobj),
        }

        headers = {}
        if content_hash:
            headers.update({
                'Content-MD5': content_hash,
            })

        response = self.oauth2_client.post(UPLOAD_FILE_URL, data=data, files=files, headers=headers)

        return response.json()

    def upload_or_update(self, parent, fileobj, content_hash=None):
        """
        Upload a file to the given parent

        This handles 409 HTTP errors and will attempt to update the existing
        file.  An optional content_hash can be passed in.  When given, the request is
        made with the `Content-MD5` header.

        :param parent: box item dictionary representing the parent folder to upload to
        :param fileobj: a file-like object to get the contents from
        :param content_hash: Optional, the file's SHA-1 hash.
        :return: (json, uploaded) tuple, Box API response JSON data and whether the file was uploaded.
                 When False, the file was updated.
        """
        try:
            response_json = self.upload(parent, fileobj, content_hash=content_hash)
        except HTTPError, exc:
            if exc.response.status_code != 409:
                raise

            error_json = exc.response.json()
            existing_file_id = error_json['context_info']['conflicts']['id']
            existing_file_etag = error_json['context_info']['conflicts']['etag']

            # update the file instead of upload it
            fileobj.seek(0, 0)  # rewind the file just in case.

            item = {'id': existing_file_id}

            response_json = self.update(
                item,
                fileobj,
                etag=existing_file_etag,
                content_hash=content_hash
            )

            uploaded = False
        else:
            uploaded = True

        return response_json, uploaded
