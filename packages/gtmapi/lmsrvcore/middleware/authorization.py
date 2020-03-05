from lmsrvcore.auth.identity import get_identity_manager_instance, AuthenticationError, tokens_from_headers
import flask


class AuthorizationMiddleware(object):
    """Middleware to enforce authentication requirements and parse JWTs

    Note: info.context.auth_middleware_has_run attribute is used to ensure that an attempt to validate tokens
    is only run once per request. If this attribute exists in info.context, the parsing and validation code is skipped.

    """
    identity_mgr = None

    def resolve(self, next, root, info, **args):
        if not self.identity_mgr:
            self.identity_mgr = get_identity_manager_instance()

        # On first field processed in request, authenticate
        if not hasattr(info.context, "auth_middleware_has_run"):
            access_token, id_token = tokens_from_headers(info.context.headers)

            # Save token to the request context for future use (e.g. look up a user's profile information if needed)
            flask.g.access_token = access_token
            flask.g.id_token = id_token

            # Check if you are authenticated, raising an AuthenticationError if you are not.
            try:
                if not self.identity_mgr.is_authenticated(access_token, id_token):
                    raise AuthenticationError("User not authenticated", 401)
            except AuthenticationError:
                raise
            finally:
                info.context.auth_middleware_has_run = True

        return next(root, info, **args)
