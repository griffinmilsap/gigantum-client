import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
mutation FetchDatasetEdgeMutation($input: FetchDatasetEdgeInput!, $first: Int!, $cursor: String, $overviewSkip: Boolean!, $activitySkip: Boolean!, $dataSkip: Boolean!, $datasetSkip: Boolean!){
    fetchDatasetEdge(input: $input){
        newDatasetEdge{
            node{
                ...Dataset_dataset
                collaborators {
                  id
                  owner
                  name
                  collaboratorUsername
                  permission
                }
                canManageCollaborators
            }
        }
        clientMutationId
    }
}
`;

const tempID = 0;


export default function FetchDatasetEdgeMutation(
  owner,
  datasetName,
  callback,
) {
  const variables = {
    input: {
      owner,
      datasetName,
    },
    first: 10,
    cursor: null,
    datasetSkip: false,
    dataSkip: false,
    overviewSkip: false,
    activitySkip: false,
  };
  commitMutation(environment, {
    mutation,
    variables,
    onCompleted: (response, error) => {
      if (error) {
        setErrorMessage(owner, datasetName, 'An error occurred while refetching data', error);
        console.log(error);
      }
      callback(error);
    },
    onError: err => console.error(err),
  });
}
