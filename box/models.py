BASE_URL = 'https://api.box.com/2.0'

FOLDERS_URL = '{}/folders/{{}}/items'.format(BASE_URL)

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

        url = FOLDERS_URL.format(folder_id)

        count = 0
        while count < limit:
            params = {
                # this is the request limit, not the number of folders we actually want
                'limit': 100,

                'offset': offset+count,
            }

            response = self.provider_logic.get(url, params=params)

            json_data = response.json()

            # if we hit the total number of entries, we have to be done
            total_count = json_data['total_count']
            if count >= total_count:
                break

            # determine how many more entries to get from the result set
            entry_count = limit - count
            entries = json_data['entries'][:entry_count]
            for entry in entries:
                yield entry

            # increment the count by the number of entries
            count += len(entries)
