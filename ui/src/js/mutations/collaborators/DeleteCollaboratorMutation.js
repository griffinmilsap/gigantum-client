import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
  mutation DeleteCollaboratorMutation($input: DeleteLabbookCollaboratorInput!){
    deleteCollaborator(input: $input){
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

export default function DeleteCollaboratorMutation(
  labbookName,
  owner,
  username,
  callback,
) {
  const variables = {
    input: {
      labbookName,
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
          setErrorMessage(owner, labbookName, `Error: Could not add Collaborator ${username}`, error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),

      updater: (store) => {


      },
    },
  );
}
