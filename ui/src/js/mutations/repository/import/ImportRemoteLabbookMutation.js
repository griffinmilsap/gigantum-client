import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// utils
import FooterUtils from 'Components/common/footer/FooterUtils';
import footerCallback from 'Components/common/footer/utils/ImportRemoteLabbook';

const mutation = graphql`
  mutation ImportRemoteLabbookMutation($input: ImportRemoteLabbookInput!){
    importRemoteLabbook(input: $input){
      jobKey
      clientMutationId
    }
  }
`;

let tempID = 0;

export default function ImportRemoteLabbookMutation(
  owner,
  labbookName,
  remoteUrl,
  successCall,
  failureCall,
  callback,
) {
  const variables = {
    input: {
      owner,
      labbookName,
      remoteUrl,
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
          type: 'importRemoteLabbook',
          key: 'jobKey',
          footerCallback,
          successCall,
          failureCall,
        };
        FooterUtils.getJobStatus(owner, labbookName, footerData);

        callback(response, error);
      },
      onError: err => console.error(err),
    },
  );
}
