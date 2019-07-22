import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';

const mutation = graphql`
  mutation ImportLabbookMutation($input: ImportLabbookInput!){
    importLabbook(input: $input){
      clientMutationId
      importJobKey
    }
  }
`;

let tempID = 0;

export default function ImportLabbookMutation(
  chunk,
  accessToken,
  idToken,
  callback,
) {
  const uploadables = [chunk.blob, accessToken, idToken];

  const variables = {
    input: {
      chunkUploadParams: {
        fileSize: chunk.fileSize,
        chunkSize: chunk.chunkSize,
        totalChunks: chunk.totalChunks,
        chunkIndex: chunk.chunkIndex,
        filename: chunk.filename,
        uploadId: chunk.uploadId,
      },
      clientMutationId: `${tempID++}`,
    },

  };
  commitMutation(
    environment,
    {
      mutation,
      variables,
      uploadables,
      onCompleted: (response, error) => {
        if (error) {
          console.log(error);
        }

        callback(response, error);
      },
      onError: err => console.error(err),

      updater: (store) => {

      },
    },
  );
}
