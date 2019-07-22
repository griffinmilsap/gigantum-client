import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
import RelayRuntime from 'relay-runtime';
import uuidv4 from 'uuid/v4';


const mutation = graphql`
  mutation AddLabbookFileMutation($input: AddLabbookFileInput!){
    addLabbookFile(input: $input){
      newLabbookFileEdge{
        node{
          id
          isDir
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


export default function AddLabbookFileMutation(
  connectionKey,
  owner,
  labbookName,
  sectionId,
  filePath,
  chunk,
  accessToken,
  idToken,
  section,
  transactionId,
  deleteId,
  callback,
) {
  const clientMutationId = uuidv4();
  const uploadables = [chunk.blob, accessToken, idToken];

  const variables = {
    input: {
      owner,
      labbookName,
      filePath,
      chunkUploadParams: {
        fileSize: chunk.fileSize,
        chunkSize: chunk.chunkSize,
        totalChunks: chunk.totalChunks,
        chunkIndex: chunk.chunkIndex,
        filename: chunk.filename,
        uploadId: chunk.uploadId,
      },
      section,
      transactionId,
      clientMutationId,
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
