import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';

const mutation = graphql`
  mutation ImportRemoteDatasetMutation($input: ImportRemoteDatasetInput!){
    importRemoteDataset(input: $input){
      newDatasetEdge{
        node{
          owner
          name
        }
      }
      clientMutationId
    }
  }
`;

let tempID = 0;

export default function ImportRemoteDatasetMutation(
  owner,
  datasetName,
  remoteUrl,
  callback,
) {
  const variables = {
    input: {
      owner,
      datasetName,
      remoteUrl,
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
      onError: err => console.error(err),

      updater: (store) => {

      },
    },
  );
}
