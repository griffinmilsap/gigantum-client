import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// utils
import FooterUtils from 'Components/common/footer/FooterUtils';

const mutation = graphql`
  mutation VerifyDatasetMutation($input: VerifyDatasetInput!){
    verifyDataset(input: $input){
      backgroundJobKey
      clientMutationId
    }
  }
`;

let tempID = 0;

export default function VerifyDatasetMutation(
  datasetOwner,
  datasetName,
  callback,
) {
  const variables = {
    input: {
      datasetOwner,
      datasetName,
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

        const footerData = {
          result: response,
          type: 'verifyDataset',
          key: 'backgroundJobKey',
          footerCallback: () => {},
          successCall: () => {},
          failureCall: () => {},
        };
        FooterUtils.getJobStatus(datasetOwner, datasetName, footerData);
        callback(response, error);
      },
      onError: err => console.error(err),

      updater: (store) => {

      },
    },
  );
}
