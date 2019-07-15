import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import RelayRuntime from 'relay-runtime';

const mutation = graphql`
  mutation DeleteSecretsFileMutation($input: DeleteSecretsFileInput!){
    deleteSecretsFile(input: $input){
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

let tempID = 0;

export default function DeleteSecretsFileMutation(
  owner,
  labbookName,
  environmentId,
  id,
  filename,
  callback,
) {
  tempID++;
  const variables = {
    input: {
      owner,
      labbookName,
      filename,
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
    },
  );
}
