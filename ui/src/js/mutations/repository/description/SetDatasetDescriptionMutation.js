import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';


const mutation = graphql`
  mutation SetDatasetDescriptionMutation($input: SetDatasetDescriptionInput!){
    setDatasetDescription(input: $input){
      clientMutationId
    }
  }
`;

let tempID = 0;


export default function SetDatasetDescriptionMutation(
  owner,
  datasetName,
  description,
  sectionId,
  callback,
) {
  const variables = {
    input: {
      owner,
      datasetName,
      description,
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
      optimisticUpdater: (store) => {
        const node = store.get(sectionId);
        if (node) {
          node.setValue(description, 'description');
        }
      },
      updater: (store, response) => {
        if (response.setDatasetDescription.clientMutationId) {
          const node = store.get(sectionId);
          if (node) {
            node.setValue(description, 'description');
          }
        }
      },
    },
  );
}
