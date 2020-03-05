import {
  commitMutation,
  graphql,
} from 'react-relay';
import uuidv4 from 'uuid/v4';
import environment from 'JS/createRelayEnvironment';

import FooterUtils from 'Components/common/footer/FooterUtils';

const mutation = graphql`
mutation ConfigureDatasetMutation($input: ConfigureDatasetInput!){
  configureDataset(input: $input){
        dataset{
          backendIsConfigured
          backendConfiguration{
            parameter
            description
            parameterType
            value
          }
        }
        isConfigured
        shouldConfirm
        errorMessage
        confirmMessage
        hasBackgroundJob
        backgroundJobKey
        clientMutationId
    }
}
`;

export default function ConfigureDatasetMutation(
  datasetOwner,
  datasetName,
  parameters,
  confirm,
  successCall,
  failureCall,
  callback,
) {
  const variables = {
    input: {
      datasetOwner,
      datasetName,
      parameters,
    },
  };
  if (confirm !== null) {
    variables.input.confirm = confirm;
  }
  const id = uuidv4();
  commitMutation(environment, {
    mutation,
    variables,
    onCompleted: (response, error) => {
      if (error) {
        console.log(error);
      }
      callback(response, error);
      if (response.configureDataset && response.configureDataset.backgroundJobKey) {
        const footerData = {
          owner: datasetOwner,
          name: datasetName,
          sectionType: 'labbook',
          result: response,
          type: 'configureDataset',
          key: 'backgroundJobKey',
          successCall,
          failureCall,
          id,
          hideFooter: true,
        };
        FooterUtils.getJobStatus(datasetOwner, datasetName, footerData);
      }
    },
    onError: err => console.error(err),
  });
}
