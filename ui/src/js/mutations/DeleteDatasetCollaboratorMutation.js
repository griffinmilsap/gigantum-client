import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
  mutation DeleteDatasetCollaboratorMutation($input: DeleteDatasetCollaboratorInput!){
    deleteDatasetCollaborator(input: $input){
      updatedDataset{
        id
        collaborators {
          id
          owner
          name
          collaboratorUsername
          permission
        }
      }
      clientMutationId
    }
  }
`;

let tempID = 0;

export default function DeleteDatasetCollaboratorMutation(
  datasetName,
  owner,
  username,
  callback,
) {
  const variables = {
    input: {
      datasetName,
      owner,
      username,
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
          setErrorMessage(`Error: Could not add Collaborator ${username}`, error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),

      updater: (store) => {


      },
    },
  );
}
