import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
mutation FetchLabbookDatasetFilesMutation($input: FetchLabbookEdgeInput!){
  fetchLabbookEdge(input: $input){
    newLabbookEdge{
      node {
        linkedDatasets{
          overview{
            numFiles
            localBytes
            totalBytes
          }
          commitsBehind
          allFiles{
            edges{
              node{
                isLocal
              }
            }
          }
        }
      }
    }
    clientMutationId
  }
}
`;

const tempID = 0;


export default function FetchLabbookDatasetFilesMutation(
  owner,
  labbookName,
  callback,
) {
  const variables = {
    input: {
      owner,
      labbookName,
    },
  };
  commitMutation(environment, {
    mutation,
    variables,
    onCompleted: (response, error) => {
      if (error) {
        console.log(error);
        setErrorMessage('An error occurred while refetching data', error);
      }
      callback(error);
    },
    onError: err => console.error(err),
  });
}
