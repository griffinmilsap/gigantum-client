# Copyright (c) 2018 FlashX, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import ast
import json
import graphene

from gtmcore.logging import LMLogger
from gtmcore.dispatcher import Dispatcher, JobKey


logger = LMLogger.get_logger()


class JobStatus(graphene.ObjectType):
    """A query to get the status of a background task launched with the Dispatcher"""
    class Meta:
        interfaces = (graphene.relay.Node,)

    # The Dispatcher returns a unique opaque id of the background job.
    job_key = graphene.Field(graphene.String)

    # Status is either: queued, failed, started, finished.
    status = graphene.Field(graphene.String)

    # Job desciption/metadata
    job_metadata = graphene.String()

    # Message if job has failed, if not in failed state this is None/null.
    failure_message = graphene.String()

    # Timestamp the task was put into the queue
    started_at = graphene.Field(graphene.String)

    # Timestamp the task was regarded as either failed or finished.
    finished_at = graphene.Field(graphene.String)

    # Result.. None if no result or void method.
    result = graphene.Field(graphene.String)

    def _loader(self):
        self.job_key = self.id
        d = Dispatcher()
        q = d.query_task(JobKey(self.job_key))
        self.status = q.status
        self.job_metadata = json.dumps(q.meta)
        self.failure_message = q.failure_message
        self.started_at = q.started_at
        self.finished_at = q.finished_at
        self.result = q.result

    def resolve_job_key(self, info):
        if self.job_key is None:
            self._loader()
        return self.job_key

    def resolve_status(self, info):
        if self.status is None:
            self._loader()
        return self.status

    def resolve_job_metadata(self, info):
        """Returns a JSON-encoded dict. NOT the dict itself. """
        if self.job_metadata is None:
            self._loader()
        return self.job_metadata

    def resolve_failure_message(self, info):
        if self.failure_message is None:
            self._loader()
        return self.failure_message

    def resolve_started_at(self, info):
        if self.started_at is None:
            self._loader()
        return self.started_at

    def resolve_finished_at(self, info):
        if self.finished_at is None:
            self._loader()
        return self.finished_at

    def resolve_result(self, info):
        if self.result is None:
            self._loader()
        return self.result

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        return JobStatus(id=id)

    def resolve_id(self, info):
        if not self.id:
            if not self.job_key:
                raise ValueError("Resolving a JobStatus Node ID requires job_key to be set")
            self.id = self.job_key
        return self.id
