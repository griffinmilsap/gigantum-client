import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
  mutation SetDatasetVisibilityMutation($input: SetDatasetVisibilityInput!){
    setDatasetVisibility(input: $input){
      newDatasetEdge{
        node{
          visibility
        }
      }
      clientMutationId
    }
  }
`;

let tempID = 0;


export default function SetDatasetVisibilityMutation(
  owner,
  datasetName,
  visibility,
  callback,
) {
  const variables = {
    input: {
      owner,
      datasetName,
      visibility,
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
    },
  );
}
