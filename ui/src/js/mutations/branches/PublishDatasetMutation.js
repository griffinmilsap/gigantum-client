import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import uuidv4 from 'uuid/v4';
import { setMultiInfoMessage } from 'JS/redux/actions/footer';
import FooterUtils from 'Components/common/footer/FooterUtils';

const mutation = graphql`
  mutation PublishDatasetMutation($input: PublishDatasetInput!){
    publishDataset(input: $input){
      jobKey
      clientMutationId
    }
  }
`;

let tempID = 0;

export default function PublishDatasetMutation(
  owner,
  datasetName,
  setPublic,
  successCall,
  failureCall,
  callback,
) {
  const variables = {
    input: {
      setPublic,
      owner,
      datasetName,
      clientMutationId: tempID++,
    },
  };
  const id = uuidv4();
  const startMessage = 'Preparing to publish Dataset...';
  setMultiInfoMessage(id, startMessage, false, false, [{ message: startMessage }]);
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
      onError: (err) => { console.error(err); },
      updater: (store, response) => {
        if (response) {
          FooterUtils.getJobStatus(response, 'publishDataset', 'jobKey', successCall, failureCall, id);
        }
      },
    },
  );
}
