import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
  mutation WriteDatasetReadmeMutation($input: WriteDatasetReadmeInput!){
    writeDatasetReadme(input: $input){
      updatedDataset {
        overview{
          id
          readme
        }
      }
      clientMutationId
    }
  }
`;

let tempID = 0;


export default function WriteDatasetReadmeMutation(
  owner,
  datasetName,
  content,
  callback,
) {
  const variables = {
    input: {
      owner,
      datasetName,
      content,
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
