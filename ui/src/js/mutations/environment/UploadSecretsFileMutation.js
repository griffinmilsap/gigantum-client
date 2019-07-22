import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';

const mutation = graphql`
  mutation UploadSecretsFileMutation($input: UploadSecretsFileInput!){
    uploadSecretsFile(input: $input){
      environment {
        secretsFileMapping {
          edges {
            node {
              id
              owner
              name
              filename
              mountPath
              isPresent
            }
          }
        }
      }
    }
  }
`;

let tempID = 0;


export default function UploadSecretsFileMutation(
  owner,
  labbookName,
  environmentId,
  id,
  filename,
  accessToken,
  idToken,
  chunk,
  transactionId,
  callback,
) {
  tempID++;

  const uploadables = [chunk.blob, accessToken, idToken];

  const variables = {
    input: {
      owner,
      labbookName,
      chunkUploadParams: {
        fileSize: chunk.fileSize,
        chunkSize: chunk.chunkSize,
        totalChunks: chunk.totalChunks,
        chunkIndex: chunk.chunkIndex,
        filename: chunk.filename,
        uploadId: chunk.uploadId,
      },
      transactionId,
      clientMutationId: `${tempID}`,
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
    },
  );
}
