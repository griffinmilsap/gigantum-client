import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import RelayRuntime from 'relay-runtime';
import uuidv4 from 'uuid/v4';


const mutation = graphql`
  mutation AddDatasetFileMutation($input: AddDatasetFileInput!){
    addDatasetFile(input: $input){
      newDatasetFileEdge{
        node{
          id
          isDir
          isLocal
          modifiedAt
          key
          size
        }
        cursor
      }
      clientMutationId
    }
  }
`;

export default function AddDatasetFileMutation(
  connectionKey,
  owner,
  datasetName,
  datasetId,
  filePath,
  chunk,
  accessToken,
  idToken,
  transactionId,
  callback,
) {
  const uploadables = [chunk.blob, accessToken, idToken];
  const id = uuidv4();

  const variables = {
    input: {
      owner,
      datasetName,
      filePath,
      chunkUploadParams: {
        fileSize: chunk.fileSize,
        chunkSize: chunk.chunkSize,
        totalChunks: chunk.totalChunks,
        chunkIndex: chunk.chunkIndex,
        filename: chunk.filename,
        uploadId: chunk.uploadId,
      },
      transactionId,
      clientMutationId: id,
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
