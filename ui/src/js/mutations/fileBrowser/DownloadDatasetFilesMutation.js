import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// utils
import FooterUtils from 'Components/common/footer/FooterUtils';
import footerCallback from 'Components/common/footer/utils/DownloadDatasetFiles';
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
mutation DownloadDatasetFilesMutation($input: DownloadDatasetFilesInput!){
    downloadDatasetFiles(input: $input){
        backgroundJobKey
        clientMutationId
    }
}
`;

let tempID = 0;


export default function DownloadDatasetFilesMutation(
  datasetOwner,
  datasetName,
  labbookName,
  labbookOwner,
  successCall,
  failureCall,
  keys,
  allKeys,
  callback,
) {
  const variables = {
    input: {
      datasetOwner,
      datasetName,
      clientMutationId: tempID++,
    },
  };
  if (allKeys) {
    variables.input.allKeys = allKeys;
  } else {
    variables.input.keys = keys;
  }
  if (labbookName) {
    variables.input.labbookName = labbookName;
  }
  if (labbookOwner) {
    variables.input.labbookOwner = labbookOwner;
  }

  commitMutation(environment, {
    mutation,
    variables,
    onCompleted: (response, error) => {
      if (error) {
        setErrorMessage(labbookOwner, labbookName, 'There was a problem downloading Dataset files', error);
        console.log(error);
      }
      const footerData = {
        result: response,
        type: 'downloadDatasetFiles',
        key: 'backgroundJobKey',
        footerCallback,
        successCall,
        failureCall,
      };

      FooterUtils.getJobStatus(datasetOwner, datasetName, footerData);

      callback(error);
    },
    onError: err => console.error(err),
  });
}
