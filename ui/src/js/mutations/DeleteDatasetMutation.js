import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import RelayRuntime from 'relay-runtime';

const mutation = graphql`
  mutation DeleteDatasetMutation($input: DeleteDatasetInput!){
    deleteDataset(input: $input){
      clientMutationId
    }
  }
`;
let tempID = 0;

function sharedUpdater(store, parentId, deletedId, connectionKey) {
  const datasetProxy = store.get(parentId);
  if (datasetProxy) {
    const conn = RelayRuntime.ConnectionHandler.getConnection(
      datasetProxy,
      connectionKey,
    );
    if (conn) {
      RelayRuntime.ConnectionHandler.deleteNode(
        conn,
        deletedId,
      );
      store.delete(deletedId);
    }
  }
}

export default function DeleteRemoteDatasetMutation(
  datasetName,
  owner,
  nodeID,
  parentID,
  connection,
  local,
  remote,
  callback,
) {
  const variables = {
    input: {
      datasetName,
      owner,
      local,
      remote,
      clientMutationId: `${tempID++}`,
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
      updater: (store, response) => {
        sharedUpdater(store, parentID, nodeID, connection);
      },
    },
  );
}
