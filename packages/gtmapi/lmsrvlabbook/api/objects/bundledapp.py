import graphene

from gtmcore.inventory.inventory import InventoryManager
from gtmcore.environment.bundledapp import BundledAppManager

from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.interfaces import GitRepository


class BundledApp(graphene.ObjectType):
    """ Represents a bundled application """
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    app_name = graphene.String(required=True, description='Name of the bundled app')
    description = graphene.String(description='Description of the bundled app')
    port = graphene.Int(description='Port on which the bundled app is exposed internally')
    command = graphene.String(description='Command to run to start the bundled app')

    def _load_app_data(self):
        lb = InventoryManager().load_labbook(get_logged_in_username(),
                                             self.owner,
                                             self.name)
        bam = BundledAppManager(lb)
        apps = bam.get_bundled_apps()
        self.description = apps[self.app_name].get('description')
        self.port = apps[self.app_name].get('port')
        self.command = apps[self.app_name].get('command')

    @classmethod
    def get_node(cls, info, id):
        owner, labbook_name, app_name = id.split('&')
        return BundledApp(owner=owner, name=labbook_name, app_name=app_name)

    def resolve_id(self, info):
        return '&'.join((self.owner, self.name, self.app_name))

    def resolve_description(self, info):
        if not self.description:
            self._load_app_data()

        return self.description

    def resolve_port(self, info):
        if not self.port:
            self._load_app_data()

        return self.port

    def resolve_command(self, info):
        if not self.command:
            self._load_app_data()

        return self.command