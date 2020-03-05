import graphene

from lmsrvcore.api.interfaces import GitRepository


class Collaborator(graphene.ObjectType):
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    # Collaborator username, using prefix to avoid potential conflict with "username"
    collaborator_username = graphene.String(required=True)

    # Collaborator permission, one of "READ_ONLY", "READ_WRITE", "OWNER"
    permission = graphene.String(required=True)

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        owner, name, collab_username, permission = id.split("&")

        return Collaborator(id='&'.join((owner, name, collab_username, permission)),
                            name=name, owner=owner, collaborator_username=collab_username,
                            permission=permission)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        return '&'.join((self.owner, self.name, self.collaborator_username, self.permission))
