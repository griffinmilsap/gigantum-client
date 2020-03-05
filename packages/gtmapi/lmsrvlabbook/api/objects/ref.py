
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
import graphene

from lmsrvcore.api.interfaces import GitRepository
from lmsrvcore.api.interfaces import GitRef

from lmsrvcore.auth.user import get_logged_in_username
from lmsrvlabbook.api.objects.commit import LabbookCommit
from lmsrvlabbook.dataloader.labbook import LabBookLoader


class LabbookRef(graphene.ObjectType):
    """An object representing a git reference in a LabBook repository"""
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository, GitRef)

    # The target commit the reference points to
    commit = graphene.Field(LabbookCommit)

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name, prefix, ref_name = id.split("&")

        return LabbookRef(id=f"{owner}&{name}&{prefix}&{ref_name}", name=name, owner=owner,
                          prefix=prefix, ref_name=ref_name,
                          _dataloader=LabBookLoader())

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name or not self.ref_name:
                raise ValueError("Resolving a LabbookRef Node ID requires owner, name, and branch to be set")
            self.id = f"{self.owner}&{self.name}&{self.prefix}&{self.ref_name}"

    def helper_resolve_commit(self, labbook):
        git_ref = labbook.git.repo.refs[self.ref_name]
        return LabbookCommit(id=f"{self.owner}&{self.name}&None&{self.ref_name}",
                             owner=self.owner, name=self.name, hash=git_ref.commit.hexsha)

    def resolve_commit(self, info):
        """Resolve the commit field"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_commit(labbook))

