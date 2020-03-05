import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
mutation LabbookLookupMutation($input: FetchLabbookEdgeInput!){
    fetchLabbookEdge(input: $input) {
        newLabbookEdge{
            node{
              environment{
                containerStatus
                imageStatus
              }
              branches {
                id
                owner
                name
                branchName
                isMergeable
                commitsBehind
                commitsAhead
              }
            }
        }
        clientMutationId
    }
}
`;

const tempID = 0;


export default function LabbookLookupMutation(
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
