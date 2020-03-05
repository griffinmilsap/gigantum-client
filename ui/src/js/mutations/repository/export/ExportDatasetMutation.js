import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';

const mutation = graphql`
  mutation ExportDatasetMutation($input: ExportDatasetInput!){
    exportDataset(input: $input){
      clientMutationId
      jobKey
    }
  }
`;

let tempID = 0;

export default function ExportDatasetMutation(
  owner,
  datasetName,
  callback,
) {
  tempID++;
  const variables = {
    input: {
      owner,
      datasetName,
      clientMutationId: `${tempID}`,
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
