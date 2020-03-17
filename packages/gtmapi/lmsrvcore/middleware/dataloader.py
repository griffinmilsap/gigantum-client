from lmsrvlabbook.dataloader.labbook import LabBookLoader
from lmsrvlabbook.dataloader.dataset import DatasetLoader


class DataloaderMiddleware(object):
    """Middleware to insert an instance of the LabBookLoader and DatasetLoader dataloaders into the request context"""
    def resolve(self, next, root, info, **args):
        if hasattr(info.context, "labbook_loader"):
            if not info.context.labbook_loader:
                info.context.labbook_loader = LabBookLoader()
        else:
            info.context.labbook_loader = LabBookLoader()

        if hasattr(info.context, "dataset_loader"):
            if not info.context.dataset_loader:
                info.context.dataset_loader = DatasetLoader()
        else:
            info.context.dataset_loader = DatasetLoader()

        return next(root, info, **args)
