// vendor
import {
  commitMutation,
  graphql,
} from 'react-relay';
import uuidv4 from 'uuid/v4';
// environment
import environment from 'JS/createRelayEnvironment';

const mutation = graphql`
  mutation CompleteBatchUploadTransactionMutation($input: CompleteBatchUploadTransactionInput!){
    completeBatchUploadTransaction(input: $input){
      clientMutationId
    }
  }
`;

export default function AddLabbookFileMutation(
  connectionKey,
  owner,
  labbookName,
  cancel,
  rollback,
  transactionId,
  callback,
) {
  const id = uuidv4();

  const variables = {
    input: {
      owner,
      labbookName,
      cancel,
      rollback,
      transactionId,
      clientMutationId: id,
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
    },
  );
}
