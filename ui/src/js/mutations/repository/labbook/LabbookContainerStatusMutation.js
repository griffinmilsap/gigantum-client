import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
mutation LabbookContainerStatusMutation($input: FetchLabbookEdgeInput!){
    fetchLabbookEdge(input: $input){
        newLabbookEdge{
          node {
            environment{
              containerStatus
              imageStatus
            }
          }
        }
        clientMutationId
    }
}
`;

const tempID = 0;


export default function LabbookContainerStatusMutation(
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
      }
      callback(error, response);
    },
    onError: err => console.error(err),
  });
}
