import AddDatasetFileMutation from 'Mutations/fileBrowser/AddDatasetFileMutation';
import AddLabbookFileMutation from 'Mutations/fileBrowser/AddLabbookFileMutation';
import ImportLabbookMutation from 'Mutations/repository/import/ImportLabbookMutation';
import ImportDatasetMutation from 'Mutations/repository/import/ImportDatasetMutation';
import UploadSecretsFileMutation from 'Mutations/environment/UploadSecretsFileMutation';

/* eslint-disable */
const addFileUpload = (data) => {
  const { file } = data;
  const {
    connection,
    owner,
    name,
    parentId,
    section,
  } = file.mutationData;
  const {
    accessToken,
    idToken,
    transactionId,
    chunkId,
  } = file;
  const {
    fullPath,
  } = file.file.entry;

  const path = file.path === '/' ? fullPath : `${file.path}${fullPath}`;
  const chunkStart = file.chunkSize * file.chunkIndex;
  const chunkEnd = (file.chunkSize * (file.chunkIndex + 1) < file.size)
    ? (file.chunkSize * (file.chunkIndex + 1))
    : file.size;
  const blob = file.file.file.slice(chunkStart, chunkEnd);

  const chunk = {
    blob,
    fileSize: `${file.size}`,
    chunkSize: file.chunkSize,
    totalChunks: file.totalChunks,
    chunkIndex: file.chunkIndex,
    filename: file.file.file.name,
    uploadId: file.uploadId,
  };

  const callback = (response, error) => {
    if(response) {
      const data = { response, chunkId };
      postMessage(data);
    } else {
      postMessage(error);
    }
  };

  if((connection === "CodeBrowser_allFiles")
    || (connection === "InputBrowser_allFiles")
    || (connection === "OutputBrowser_allFiles")) {

    AddLabbookFileMutation(
      connection,
      owner,
      name,
      parentId,
      path,
      chunk,
      accessToken,
      idToken,
      section,
      transactionId,
      [],
      callback,
    );
  } else if (connection === "DataBrowser_allFiles") {

    AddDatasetFileMutation(
      connection,
      owner,
      name,
      parentId,
      path,
      chunk,
      accessToken,
      idToken,
      transactionId,
      callback,
    );
  }
}

const importFileUpload = (data, connection) => {
  const { file } = data;
  const {
    accessToken,
    idToken,
    transactionId,
    chunkId,
  } = file;
  const {
    owner,
    name,
    environmentId,
    id,
    filename,
  } = file.mutationData;
  const {
    fullPath,
  } = file.file.entry;
  const path = `${file.path}${fullPath}`;

  const chunkStart = file.chunkSize * file.chunkIndex;
  const chunkEnd = (file.chunkSize * (file.chunkIndex + 1) < file.size)
    ? file.chunkSize * (file.chunkIndex + 1)
    : file.size;
  const blob = file.file.file.slice(chunkStart, chunkEnd);

  const chunk = {
    blob,
    fileSize: `${file.size}`,
    chunkSize: file.chunkSize,
    totalChunks: file.totalChunks,
    chunkIndex: file.chunkIndex,
    filename: file.file.file.name,
    uploadId: transactionId,
  };

  const callback = (response, error) => {
    if(response) {
      const data = { response, chunkId };
      postMessage(data);
    } else {
      postMessage(error);
    }
  };

  if(connection === "ImportLabbookMutation") {

    ImportLabbookMutation(
      chunk,
      accessToken,
      idToken,
      callback,
    );
  } else if (connection === "ImportDatasetMutation") {

    ImportDatasetMutation(
      chunk,
      accessToken,
      idToken,
      callback,
    );
  } else if (connection === 'Secrets_secretsFileMapping') {
    UploadSecretsFileMutation(
      owner,
      name,
      environmentId,
      id,
      filename,
      accessToken,
      idToken,
      chunk,
      transactionId,
      callback,
    )
  }
}


self.addEventListener('message', (evt) => {
  const { data } = evt;
  const { connection } = data.file.mutationData;
  if (connection.indexOf('allFiles') > -1) {
     addFileUpload(data);
  } else {
    importFileUpload(data, connection);
  }
});
