import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
  mutation AddCollaboratorMutation($input: AddLabbookCollaboratorInput!){
    addCollaborator(input: $input){
      updatedLabbook{
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
  labbookName,
  owner,
  username,
  permissions,
  callback,
) {
  const variables = {
    input: {
      labbookName,
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
          setErrorMessage(owner, labbookName, `ERROR: Could not add Collaborator ${username}`, error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),
    },
  );
}
