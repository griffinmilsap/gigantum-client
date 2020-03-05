from typing import Optional, Dict, Callable, Any, List, Tuple
import aiohttp
import asyncio

from gtmcore.dataset.manifest.eventloop import get_event_loop


class ConcurrentRequest(object):
    """Class for a URL to be resolved concurrently

    Currently only supports GETs and json or text, but future extension could support other REST verbs and binary data
    """
    def __init__(self, url: str, params: Optional[Dict[str, str]] = None, headers: Optional[dict] = None,
                 extraction_function: Optional[Callable] = None, timeout: int = 60) -> None:
        self.url = url
        self.params = params
        self.timeout = timeout
        self.headers = headers

        # Set this to a function you want called to process the response and set the extracted_value
        self.extraction_function = extraction_function

        # Results
        self.status_code: Optional[int] = None
        self.content_type: Optional[str] = None
        self.content_length: Optional[int] = None
        self.json: Optional[dict] = None
        self.text: Optional[str] = None
        self.error: Optional[str] = None

    @property
    def extracted_text(self) -> Any:
        """If self.extraction_function is set to a function, calling this attribute will process the data for you"""
        if not self.extraction_function:
            raise ValueError("Extraction Function not set. Only full response data access possible.")
        return self.extraction_function(self.text)

    @property
    def extracted_json(self) -> Any:
        """If self.extraction_function is set to a function, calling this attribute will process the data for you"""
        if not self.extraction_function:
            raise ValueError("Extraction Function not set. Only full response data access possible.")
        return self.extraction_function(self.json)


class ConcurrentRequestManager(object):
    """Class to manage processing async requests"""
    def __init__(self, timeout: int = 60, semaphore_limit: int = 1000) -> None:
        self.timeout = timeout
        self._client_session: Optional[aiohttp.ClientSession] = None

        self.semaphore_limit = semaphore_limit
        self._semaphore: Optional[asyncio.Semaphore] = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Property to get a sesssion. Only one should exist at a time, so keep returning the same session.

        Returns:

        """
        if not self._client_session:
            self._client_session = aiohttp.ClientSession()
        return self._client_session

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Property to get an asyncio.Semaphore. Only one should exist at a time, so keep returning the same semaphore.

        Returns:
             asyncio.Semaphore
        """
        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self.semaphore_limit)
        return self._semaphore

    async def _fetch(self, url_obj: ConcurrentRequest) -> ConcurrentRequest:
        """Private method to resolve a URL and parse it.

        Args:
            url_obj: ConcurrentRequest object to get and resolve

        Returns:
            ConcurrentRequest
        """
        async with self.session.get(url_obj.url, params=url_obj.params,
                                    headers=url_obj.headers, timeout=url_obj.timeout) as response:
            url_obj.status_code = response.status
            url_obj.content_type = response.content_type
            url_obj.content_length = response.content_length
            if "json" in response.content_type:
                url_obj.json = await response.json()
            elif "text" in response.content_type:
                url_obj.text = await response.text()
            else:
                url_obj.error = f"Unsupported content-type: {response.content_type}"

        return url_obj

    async def _bound_fetch(self, url_obj: ConcurrentRequest) -> ConcurrentRequest:
        """Wrapper to limit concurrency"""
        async with self.semaphore:
            return await self._fetch(url_obj)

    async def _resolve_worker(self, url_objs: List[ConcurrentRequest]) -> List:
        """Method to gather all resolve tasks"""
        tasks = list()
        for url_obj in url_objs:
            task = asyncio.ensure_future(self._bound_fetch(url_obj))
            tasks.append(task)

        responses = asyncio.gather(*tasks)
        return await responses

    def resolve(self, url_obj: ConcurrentRequest) -> ConcurrentRequest:
        """Method to resolve a single ConcurrentRequest object

        Args:
            url_obj(ConcurrentRequest): ConcurrentRequest object to resolve

        Returns:
            ConcurrentRequest
        """
        loop = get_event_loop()
        future = asyncio.ensure_future(self._resolve_worker([url_obj]))
        result = loop.run_until_complete(future)
        return result[0]

    def resolve_many(self, url_objs: List[ConcurrentRequest]) -> List[ConcurrentRequest]:
        """Method to resolve a many ConcurrentRequest objects

        Args:
            url_objs(list): ConcurrentRequest object to resolve

        Returns:
            list
        """
        loop = get_event_loop()
        future = asyncio.ensure_future(self._resolve_worker(url_objs))
        result = loop.run_until_complete(future)
        return result
