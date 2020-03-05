import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
  mutation WriteLabbookReadmeMutation($input: WriteLabbookReadmeInput!){
    writeLabbookReadme(input: $input){
      updatedLabbook {
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


export default function WriteLabbookReadmeMutation(
  owner,
  labbookName,
  content,
  callback,
) {
  const variables = {
    input: {
      owner,
      labbookName,
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
