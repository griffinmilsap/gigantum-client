from typing import Optional
import graphene
from gtmcore.logging import LMLogger
from lmsrvlabbook.dataloader.package import PackageDataloader

logger = LMLogger.get_logger()


class PackageComponentInput(graphene.InputObjectType):
    """An input type to support Batch interfaces that use Package Components"""

    # The name of the package manager
    manager = graphene.String(required=True)

    # The name of the package
    package = graphene.String(required=True)

    # The desired version of the package
    version = graphene.String()


class PackageComponent(graphene.ObjectType):
    """A type that represents a Package Manager based Environment Component"""
    # The dataloader used to get package metadata
    class Meta:
        interfaces = (graphene.relay.Node,)

    _dataloader: Optional[PackageDataloader] = None

    # The Component schema version
    schema = graphene.Int()

    # The name of the package manager
    manager = graphene.String(required=True)

    # The name of the package
    package = graphene.String(required=True)

    # The current version of the package
    version = graphene.String()

    # The latest available version of the package
    latest_version = graphene.String()

    # The package's description
    description = graphene.String()

    # A URL for access the package's docs
    docs_url = graphene.String()

    # Flag indicating if the component is in the Base
    from_base = graphene.Boolean()

    # Flag indicating if the package name and version has been validated
    is_valid = graphene.Boolean(default_value=False)

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        manager, package, version = id.split("&")

        if version == 'INVALID':
            version = None

        return PackageComponent(id=f"{manager}&{package}&{version}",
                                manager=manager, package=package, version=version)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.manager or not self.package:
            raise ValueError("Resolving a PackageComponent ID requires manager and package to be set")

        if self.version is None:
            version_key = 'INVALID'
        else:
            version_key = self.version

        return f"{self.manager}&{self.package}&{version_key}"

    def resolve_latest_version(self, info):
        """Resolve the latest_version field"""
        if self.latest_version is not None:
            return self.latest_version

        if self.version is None:
            # Package name is invalid, so can't resolve any further info
            return None

        if not self._dataloader:
            # No dataloader is available
            logger.warning(f"Cannot query for latest version of {self.package}. A labbook context is required")
            return None

        # If you get here, load via dataloader (which has labbook context)
        return self._dataloader.load(f"{self.manager}&{self.package}").then(lambda metadata: metadata.latest_version)

    def resolve_description(self, info):
        """Resolve the description field"""
        if self.description is not None:
            return self.description

        if self.version is None:
            # Package name is invalid, so can't resolve any further info
            return None

        if not self._dataloader:
            # No dataloader is available
            logger.warning(f"Cannot query for description of {self.package}. A labbook context is required")
            return None

        # If you get here, load via dataloader (which has labbook context)
        return self._dataloader.load(f"{self.manager}&{self.package}").then(lambda metadata: metadata.description)

    def resolve_docs_url(self, info):
        """Resolve the docs_url field"""
        if self.docs_url is not None:
            return self.docs_url

        if self.version is None:
            # Package name is invalid, so can't resolve any further info
            return None

        if not self._dataloader:
            # No dataloader is available
            logger.warning(f"Cannot query for docs_urln of {self.package}. A labbook context is required")
            return None

        # If you get here, load via version dataloader (which has labbook context)
        return self._dataloader.load(f"{self.manager}&{self.package}").then(lambda metadata: metadata.docs_url)

    def resolve_from_base(self, info):
        """Resolve the from_base field"""
        if self.from_base is None:
            # Assume not from base if value is not set on construction
            return False
        else:
            return self.from_base
