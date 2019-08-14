from typing import Dict, Tuple
from itertools import product

from gtmcore.logging import LMLogger
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.caching import LabbookCacheController, DatasetCacheController

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
                self.flush_repo_cache(info.operation, info.variable_values)
            except UnknownRepo as e:
                logger.warning(f'Mutation {info.operation.name} not associated with a repo: {e}')
            except SkipRepo:
                logger.debug(f'Skip {info.operation.name}')
            finally:
                info.context.repo_cache_middleware_complete = True

        return_value = next(root, info, **args)
        return return_value

    def flush_repo_cache(self, operation_obj, variable_values: Dict) -> None:
        """ Clears the cache for ANY labbook or dataset that has attributes matching
        any input field. This method will likely overestimate and remove too many
        cache items, but we accept the cost as it will lead to fewer potential problems.

        Input:
            operation_obj: Reference to the actual Graphene GraphQL mutation
            variable_values: Dict containing the mutation Input fields

        Returns:
            None
        """
        input_vals = variable_values.get('input')
        if input_vals is None:
            raise UnknownRepo("No input section to mutation")

        # Indicates this mutation is really a query.
        if operation_obj.name.value in self.skip_mutations:
            raise SkipRepo(f"Skip mutation {operation_obj.name}")

        owners = [owner for owner in (input_vals.get('owner'),
                                      input_vals.get('labbook_owner'),
                                      input_vals.get('dataset_owner'))
                  if owner]
        if not owners:
            raise UnknownRepo("No repository owner detected")

        names = [name for name in (input_vals.get('name'),
                                   input_vals.get('labbook_name'),
                                   input_vals.get('dataset_name'))
                 if name]
        if not names:
            raise UnknownRepo("No repository name detected")

        # Here we go through and delete any and all cache entries for labbooks
        # or datasets that match the input attributes. It in some cases may be
        # a bit too aggressive in deleting a single cache entry, but we consider
        # it worth the extremely minor cost to refetch a single repo.
        #
        # It must continue to be this way until we have a more structured way to
        # discriminate whether the given mutation is for a Dataset or Labbook.
        lb_cache, ds_cache = LabbookCacheController(), DatasetCacheController()
        for owner, name in product(owners, names):
            lb_cache.clear_entry((get_logged_in_username(), owner, name))
            ds_cache.clear_entry((get_logged_in_username(), owner, name))
