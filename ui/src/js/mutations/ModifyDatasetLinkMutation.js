import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
  mutation ModifyDatasetLinkMutation($input: ModifyDatasetLinkInput!){
    modifyDatasetLink(input: $input){
          newLabbookEdge{
              node{
                id
                name
                linkedDatasets {
                  overview{
                    numFiles
                    localBytes
                    totalBytes
                  }
                  name
                  owner
                  commitsBehind
                  allFiles{
                    edges{
                      node{
                        id
                        owner
                        name
                        key
                        isDir
                        isLocal
                        modifiedAt
                        size
                      }
                    }
                  }
                }
              }
          }
      }
  }
  `;

let tempID = 0;


export default function ModifyDatasetLinkMutation(
  labbookOwner,
  labbookName,
  datasetOwner,
  datasetName,
  action,
  datasetUrl,
  callback,
) {
  const variables = {
    input: {
      labbookOwner,
      labbookName,
      datasetOwner,
      datasetName,
      action,
      datasetUrl,
      clientMutationId: tempID++,
    },
  };
  commitMutation(environment, {
    mutation,
    variables,
    onCompleted: (response, error) => {
      if (error) {
        console.log(error);
      }
      callback(response, error);
    },
    onError: err => console.error(err),
    optimisticUpdater: (store, response) => {
    },
    updater: (store, response) => {
    },
  });
}
