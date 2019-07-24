import base64
import gzip
import json
from typing import Dict


class RserverExchange:
    """Data-oriented class to simplify dealing with RStudio messages decoded from the MITM log

    Attributes are stored in a way that is ready for activity records. bytes get decoded, and images get
    base64-encoded.

    """

    def __init__(self, raw_message: Dict):
        """Note, parsing may throw a json.JSONDecodeError (though it shouldn't!)"""
        self.path = raw_message['request']['path'].decode()
        self.request_headers = {k.decode(): v.decode() for k, v in raw_message['request']['headers']}

        request_text = raw_message['request']['content']
        if request_text:
            self.request = json.loads(request_text.decode())
        else:
            self.request = None

        self.response_headers = {k.decode(): v.decode() for k, v in raw_message['response']['headers']}
        self.response_type = self.response_headers.get('Content-Type')

        # This could get fairly resource intensive if our records get large,
        # but for now we keep things simple - all parsing happens in this class, and we can optimize later
        response_bytes = raw_message['response']['content']
        if self.response_headers.get('Content-Encoding') == 'gzip':
            response_bytes = gzip.decompress(response_bytes)

        # Default response is empty string
        if self.response_type == 'application/json':
            # strict=False allows control codes, as used in tidyverse output
            self.response = json.loads(response_bytes.decode(), strict=False)
        elif self.response_type == 'image/png':
            self.response = base64.b64encode(response_bytes).decode('ascii')
            # if we actually wanted to work with the image, could do so like this:
            # img = Image.open(io.BytesIO(response_bytes))
        elif response_bytes:
            self.response = '**unsupported**'
        else:
            self.response = ''