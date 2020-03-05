import graphene
from gtmcore.dataset.storage import get_storage_backend


class DatasetType(graphene.ObjectType):
    """A type that represents a type of Dataset that can be created"""
    class Meta:
        interfaces = (graphene.relay.Node, )

    # The loaded yaml data
    _dataset_type_data = None

    # Human readable name
    name = graphene.String()

    # Unique identifier for the Dataset Type
    storage_type = graphene.String()

    # Boolean indicating if type is fully managed
    is_managed = graphene.Boolean()

    # Boolean indicating if type can automatically update the manifest from the remote storage backend
    can_update_unmanaged_from_remote = graphene.Boolean()

    # Short description of the Dataset Type
    description = graphene.String()

    # Arbitrary markdown description of the Dataset Type
    readme = graphene.String()

    # Tags that can be used when searching/filtering components
    tags = graphene.List(graphene.String)

    # Base64 encoded image
    icon = graphene.String()

    # Url to more documentation or info about the base
    url = graphene.String()

    def _load_info(self):
        """Private method to load the metadata for the Type"""
        if not self._dataset_type_data:
            sb = get_storage_backend(self.storage_type)

            self._dataset_type_data = sb.metadata
            self._dataset_type_data['is_managed'] = sb.is_managed
            if sb.is_managed is False:
                self._dataset_type_data['can_update_unmanaged_from_remote'] = sb.can_update_from_remote
            else:
                self._dataset_type_data['can_update_unmanaged_from_remote'] = False

        self.name = self._dataset_type_data['name']
        self.description = self._dataset_type_data['description']
        self.readme = self._dataset_type_data['readme']
        self.tags = self._dataset_type_data['tags']
        self.icon = self._dataset_type_data['icon']
        self.url = self._dataset_type_data['url']
        self.is_managed = self._dataset_type_data['is_managed']
        self.can_update_unmanaged_from_remote = self._dataset_type_data['can_update_unmanaged_from_remote']

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        return DatasetType(id=id, storage_type=id)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if self.storage_type is None:
            raise ValueError("Resolving a DatasetType ID requires storage_type to be set")

        return self.storage_type

    def resolve_name(self, info):
        """Resolve the name field"""
        if self.name is None:
            self._load_info()
        return self.name

    def resolve_description(self, info):
        """Resolve the description field"""
        if self.description is None:
            self._load_info()
        return self.description

    def resolve_is_managed(self, info):
        """Resolve the is_managed field"""
        if self.is_managed is None:
            self._load_info()
        return self.is_managed

    def resolve_readme(self, info):
        """Resolve the readme field"""
        if self.readme is None:
            self._load_info()
        return self.readme

    def resolve_tags(self, info):
        """Resolve the tags field"""
        if self.tags is None:
            self._load_info()
        return self.tags

    def resolve_icon(self, info):
        """Resolve the icon field"""
        if self.icon is None:
            self._load_info()
        return self.icon

    def resolve_url(self, info):
        """Resolve the url field"""
        if self.url is None:
            self._load_info()
        return self.url

    def resolve_can_update_unmanaged_from_remote(self, info):
        """Resolve the tags field"""
        if self.can_update_unmanaged_from_remote is None:
            self._load_info()
        return self.can_update_unmanaged_from_remote
