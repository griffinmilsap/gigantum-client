// vendor
import {
  commitMutation,
  graphql,
} from 'react-relay';
import RelayRuntime from 'relay-runtime';
import uuidv4 from 'uuid/v4';
// environment
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
  mutation InsertSecretsEntryMutation($input: InsertSecretsEntryInput!){
    insertSecretsEntry(input: $input){
      environment {
        secretsFileMapping {
          edges {
            node {
              id
              owner
              name
              filename
              mountPath
              isPresent
            }
          }
        }
      }
    }
  }
`;

/**
  @param {object, string, object} store,id,newEdge
  gets a connection to the store and insets an edge if connection is Successful
*/
function sharedUpdater(store, id, node) {
  const sharedProxy = store.get(id);
  if (sharedProxy) {
    const conn = RelayRuntime.ConnectionHandler.getConnection(
      sharedProxy,
      'Secrets_secretsFileMapping',
      [],
    );
    if (conn) {
      const edge = RelayRuntime.ConnectionHandler.createEdge(
        store,
        conn,
        node,
        'secretsEdge',
      );

      RelayRuntime.ConnectionHandler.insertEdgeAfter(conn, edge);
    }
  }
}

export default function InsertSecretsEntryMutation(
  owner,
  labbookName,
  environmentId,
  filename,
  mountPath,
  callback,
) {
  const variables = {
    input: {
      owner,
      labbookName,
      filename,
      mountPath,
      clientMutationId: uuidv4(),
    },
  };

  commitMutation(
    environment,
    {
      mutation,
      variables,
      onCompleted: (response, error) => {
        if (error) {
          console.log(error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),
      updater: (store, response) => {
        if (response.insertSecretsEntry) {
          const newEdges = response.insertSecretsEntry.environment.secretsFileMapping.edges;
          const edge = newEdges.filter(({ node }) => node.filename === filename)[0];
          const node = store.get(edge.node.id) ? store.get(edge.node.id) : store.create(edge.node.id, 'Secret');
          node.setValue(edge.node.id, 'id');
          node.setValue(edge.node.owner, 'owner');
          node.setValue(edge.node.name, 'name');
          node.setValue(edge.node.filename, 'filename');
          node.setValue(edge.node.mountPath, 'mountPath');
          node.setValue(edge.node.isPresent, 'isPresent');
          sharedUpdater(store, environmentId, node);
        }
      },
    },
  );
}
