import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import RelayRuntime from 'relay-runtime';

const mutation = graphql`
  mutation CreateDatasetMutation($input: CreateDatasetInput!){
    createDataset(input: $input){
      dataset{
        id
        name
        owner
      }
    }
  }
`;

let tempID = 0;
export default function CreateDatasetMutation(
  name,
  description,
  storageType,
  callback,
) {
  const variables = {
    input: {
      name,
      description,
      storageType,
      callback,
      clientMutationId: tempID++,
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
      updater: (store) => {
        const id = `client:newDataset:${tempID++}`;
        const node = store.create(id, 'Dataset');

        node.setValue(name, 'name');
        node.setValue(description, 'description');

        const datasetProxy = store.get('client:root');

        const conn = RelayRuntime.ConnectionHandler.getConnection(
          datasetProxy,
          'LocalDatasets_localDatasets',
        );

        if (conn) {
          RelayRuntime.ConnectionHandler.createEdge(
            store,
            conn,
            node,
            'DatasetEdge',
          );
          // RelayRuntime.ConnectionHandler.insertEdgeAfter(conn, newEdge)
        }
      },
    },
  );
}

export { mutation };
