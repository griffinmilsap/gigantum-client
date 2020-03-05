# Copyright (c) 2017 FlashX, LLC
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
from lmsrvcore.api.interfaces import User
from lmsrvcore.auth.user import get_logged_in_user
from lmsrvcore.auth.identity import get_identity_manager_instance
import flask


class UserIdentity(graphene.ObjectType):
    """A type representing the identity of the logged in user"""
    class Meta:
        interfaces = (graphene.relay.Node, User)

    is_session_valid = graphene.Boolean()

    @classmethod
    def get_node(cls, info, id):
        raise ValueError("Cannot load UserIdentity Objects from node ID due to authentication restrictions.")

    def _set_user_fields(self):
        """Private method to set all the fields of this instance"""
        try:
            user = get_logged_in_user()
            self.username = user.username
            self.email = user.email
            self.given_name = user.given_name
            self.family_name = user.family_name
        except AttributeError:
            # Current user not loaded
            pass

    def resolve_id(self, info):
        """Method to parse an ID for a given type into its identifiable variables returned as a dictionary of strings

        Args:
            info: Graphene info object

        Returns:
            dict
        """
        if not self.username:
            self._set_user_fields()
        return self.username

    def resolve_username(self, info):
        """Return the username field

        Args:
            info: Graphene info object

        Returns:
            dict
        """
        if not self.username:
            self._set_user_fields()
        return self.username

    def resolve_email(self, info):
        """Return the email field

        Args:
            info: Graphene info object

        Returns:
            dict
        """
        if not self.email:
            self._set_user_fields()
        return self.email

    def resolve_given_name(self, info):
        """Return the given_name field

        Args:
            info: Graphene info object

        Returns:
            dict
        """
        if not self.given_name:
            self._set_user_fields()
        return self.given_name

    def resolve_family_name(self, info):
        """Return the family_name field

        Args:
            info: Graphene info object

        Returns:
            dict
        """
        if not self.family_name:
            self._set_user_fields()
        return self.family_name

    def resolve_is_session_valid(self, info):
        """Return the is_session_valid field

        Args:
            info: Graphene info object

        Returns:
            dict
        """
        # Load the current identity manager and check the token, provided by the request context
        return get_identity_manager_instance().is_token_valid(flask.g.get('access_token', None))
