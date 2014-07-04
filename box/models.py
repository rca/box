BASE_URL = 'https://api.box.com/2.0'

FOLDERS_URL = '{}/folders'.format(BASE_URL)
FOLDER_LIST_URL = '{}/{{}}/items'.format(FOLDERS_URL)

MAX_FOLDERS = 1000


class Client(object):
    def __init__(self, provider_logic):
        """
        Box client constructor
        :param provider_logic: oauthclient ProviderLogic instance
        :return:
        """
        self.provider_logic = provider_logic

    def folders(self, parent=None, limit=100, offset=0):
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
