import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
mutation FetchDatasetFilesMutation($input: FetchDatasetEdgeInput!){
    fetchDatasetEdge(input: $input){
        newDatasetEdge{
          node {
            allFiles {
              edges {
                node {
                  isLocal
                }
              }
            }
          }
        }
        clientMutationId
    }
}
`;


export default function FetchDatasetFilesMutation(
  owner,
  datasetName,
  callback,
) {
  const variables = {
    input: {
      owner,
      datasetName,
    },
  };
  commitMutation(environment, {
    mutation,
    variables,
    onCompleted: (response, error) => {
      if (error) {
        setErrorMessage(owner, datasetName, 'An error occurred while refetching data', error);
      }
      callback(error);
    },
    onError: err => console.error(err),
  });
}
