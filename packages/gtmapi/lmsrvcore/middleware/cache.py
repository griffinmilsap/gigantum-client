from typing import Dict, Tuple

from gtmcore.logging import LMLogger
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.caching import RepoCacheController

logger = LMLogger.get_logger()


class UnknownRepo(Exception):
    """Indicates the given mutation cannot be inferred from the captured arguments. """
    pass


class SkipRepo(Exception):
    """Indicates the mutation in question should be skipped, as it is a special case mutation. """
    pass


class RepositoryCacheMiddleware:
    # TODO/Question - Can we directly import these mutations
    # OR can we add some optional metadata to the mutation definitions
    # themselves in order to let-them self-identify as mutations to skip
    skip_mutations = [
        'LabbookContainerStatusMutation',
        'LabbookLookupMutation'
    ]

    def resolve(self, next, root, info, **args):
        """This segment of the middleware attempts to capture specific mutations and use the
        info for given repositories to flush the corresponding cache input.

        For example, if you stop a Project container, this callback will capture the owner
        and repository name, and then flush the Redis cache for that repo. Basically, any
        mutation on the repo will flush its cache. """
        if hasattr(info.context, "repo_cache_middleware_complete"):
            # Ensure that this is called ONLY once per request.
            return next(root, info, **args)

        if info.operation.operation == 'mutation':
            try:
                username, owner, name = self.parse_mutation(info.operation, info.variable_values)
                r = RepoCacheController()
                r.clear_entry((username, owner, name))
            except UnknownRepo as e:
                logger.warning(f'Mutation {info.operation.name} not associated with a repo: {e}')
            except SkipRepo:
                logger.debug(f'Skip {info.operation.name}')
            finally:
                info.context.repo_cache_middleware_complete = True

        return_value = next(root, info, **args)
        return return_value

    def parse_mutation(self, operation_obj, variable_values: Dict) -> Tuple[str, str, str]:
        """ Infers and extracts a repository (Labbook/Dataset) owner and name field from a given
        mutation. Note that there are somewhat inconsistent namings in certain Mutation inputs,
        so this method uses a variety of methods to capture it.

        Input:
            operation_obj: Reference to the actual Graphene GraphQL mutation
            variable_values: Dict containing the mutation Input fields

        Returns:
            Tuple indicating username, owner, and repo name
        """
        input_vals = variable_values.get('input')
        if input_vals is None:
            raise UnknownRepo("No input section to mutation")

        # Indicates this mutation is really a query.
        if operation_obj.name.value in self.skip_mutations:
            raise SkipRepo(f"Skip mutation {operation_obj.name}")

        owner = input_vals.get('owner')
        if not owner:
            owner = input_vals.get('labbook_owner')
        # TODO! Include support for datasets.
        #if not owner:
        #    owner = input_vals.get('dataset_owner')
        if owner is None:
            raise UnknownRepo("No repository owner detected")

        repo_name = input_vals.get('name')
        if not repo_name:
            repo_name = input_vals.get('labbook_name')
        # TODO! Include support for datasets.
        #if not repo_name:
        #    repo_name = input_vals.get('dataset_name')

        if repo_name is None:
            raise UnknownRepo("No repository name detected")

        return get_logged_in_username(), owner, repo_name


