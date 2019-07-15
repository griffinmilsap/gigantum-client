from gtmcore.http import ConcurrentRequestManager, ConcurrentRequest
import time
import pytest
import asyncio


class TestAsyncHTTP(object):
    def test_resolve_many_200(self):
        request1 = ConcurrentRequest('https://jsonplaceholder.typicode.com/todos/1')
        arm = ConcurrentRequestManager()
        result = arm.resolve_many([request1])
        assert isinstance(result, list)
        assert isinstance(result[0], ConcurrentRequest)
        assert 'userId' in result[0].json

    def test_get_many(self):
        request_list = list()
        for _ in range(500):
            request_list.append(ConcurrentRequest("https://httpstat.us/200?sleep=100"))

        request_list.append(ConcurrentRequest("https://httpstat.us/200?sleep=5000"))
        request_list.append(ConcurrentRequest("https://httpstat.us/200?sleep=5000"))
        request_list.append(ConcurrentRequest("https://httpstat.us/200?sleep=5000"))
        request_list.append(ConcurrentRequest("https://httpstat.us/200?sleep=5000"))

        t_start = time.time()
        arm = ConcurrentRequestManager()
        result = arm.resolve_many(request_list)
        t_stop = time.time()
        assert len(result) == 504

        print((t_stop - t_start))

        # If the requests ran serially, it should take 70 seconds. If concurrent it should be faster.
        # Check to make sure it's less than 30 seconds due to variability in httpstat.us when we slam it
        assert (t_stop - t_start) < 35

        for r in result:
            assert r.status_code == 200
            assert r.text == '200 OK'

    def test_resolve_200(self):
        request1 = ConcurrentRequest('https://jsonplaceholder.typicode.com/todos/1')
        arm = ConcurrentRequestManager()
        response = arm.resolve(request1)
        assert isinstance(response, ConcurrentRequest)
        assert 'userId' in response.json

    def test_api_error(self):
        req = ConcurrentRequest("https://httpstat.us/404?sleep=100")
        arm = ConcurrentRequestManager()
        response = arm.resolve(req)
        assert "json" not in response.content_type
        assert "text" in response.content_type
        assert response.status_code == 404
        assert response.text == '404 Not Found'

    def test_resolve_extraction(self):
        def test_extractor(data):
            return data['userId']

        request1 = ConcurrentRequest('https://jsonplaceholder.typicode.com/todos/2', extraction_function=test_extractor)
        arm = ConcurrentRequestManager()
        response = arm.resolve(request1)
        assert response.extracted_json == 1

    def test_timeout(self):
        req = ConcurrentRequest("https://httpstat.us/200?sleep=10000", timeout=1)
        arm = ConcurrentRequestManager()
        with pytest.raises(asyncio.TimeoutError):
            arm.resolve(req)

    def test_failover_to_text(self):
        request1 = ConcurrentRequest('https://pypi.python.org/pypi/asdfasdfasdfasdf/json')
        arm = ConcurrentRequestManager()
        response = arm.resolve(request1)
        assert isinstance(response, ConcurrentRequest)
        assert "text" in response.content_type
        assert len(response.text) > 100
        assert response.content_length > 100
        assert response.error is None

    def test_unsupported_mimetype(self):
        request1 = ConcurrentRequest('https://s3.amazonaws.com/io.gigantum.assets/circle-logo.png')
        arm = ConcurrentRequestManager()
        response = arm.resolve(request1)
        assert isinstance(response, ConcurrentRequest)
        assert "image/png" == response.content_type
        assert response.text is None
        assert response.json is None
        assert response.error == "Unsupported content-type: image/png"
