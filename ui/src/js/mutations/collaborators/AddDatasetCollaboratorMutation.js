import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
  mutation AddDatasetCollaboratorMutation($input: AddDatasetCollaboratorInput!){
    addDatasetCollaborator(input: $input){
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

export default function AddCollaboratorMutation(
  datasetName,
  owner,
  username,
  permissions,
  callback,
) {
  const variables = {
    input: {
      datasetName,
      owner,
      username,
      permissions,
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
          setErrorMessage(owner, datasetName, `ERROR: Could not add Collaborator ${username}`, error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),
    },
  );
}
