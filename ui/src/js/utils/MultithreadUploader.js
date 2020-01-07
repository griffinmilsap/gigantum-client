// vendor
import uuidv4 from 'uuid/v4';

// store
import {
  setUploadMessageUpdate,
  setUploadMessageRemove,
  setErrorMessage,
} from 'JS/redux/actions/footer';
// mutations
import CompleteBatchUploadTransactionMutation
  from 'Mutations/fileBrowser/CompleteBatchUploadTransactionMutation';
import CompleteDatasetUploadTransactionMutation
  from 'Mutations/fileBrowser/CompleteDatasetUploadTransactionMutation';
// footer utils
import FooterUtils from 'Components/common/footer/FooterUtils';
import UpdateFileBrowserStore from 'Mutations/localCommits/FileBrowserStore';
import UpdateSecretsStore from 'Mutations/localCommits/SecretsStore';


const chunkSize = 16 * 1000 * 1000;

/**
* Returns data about the file upload
* @param {Array} files
*
* @return {Object}
*/
const configureUploadData = (config, transactionId) => {
  const {
    files,
    path,
    mutationData,
  } = config;

  let totalSize = 0;


  const filesData = [];
  const accessToken = localStorage.getItem('access_token');
  const idToken = localStorage.getItem('id_token');
  const lastChunks = [];

  files.forEach((file) => {
    totalSize += file.file.size;
    const totalChunks = Math.ceil(file.file.size / chunkSize);

    let fileSize = 0;
    let chunkIndex = 0;
    const uploadId = uuidv4();

    while (fileSize < file.file.size) {
      const addedChunksTotal = (chunkSize * (chunkIndex + 1));
      fileSize = addedChunksTotal > file.file.size ? file.file.size : addedChunksTotal;
      const chunk = {
        file,
        path,
        mutationData,
        accessToken,
        idToken,
        transactionId,
        chunkSize,
        totalChunks,
        chunkIndex,
        uploadId,
        size: file.file.size,
        sizeUploaded: 0,
        proccessed: false,
        chunkId: uuidv4(),
      };

      if ((addedChunksTotal < file.file.size) || (chunkIndex === 0)) {
        filesData.push(chunk);
      } else {
        lastChunks.push(chunk);
      }
      chunkIndex += 1;
    }

    if (file.file.size === 0) {
      const chunk = {
        file,
        path,
        mutationData,
        accessToken,
        idToken,
        transactionId,
        chunkSize: 0,
        totalChunks: 1,
        chunkIndex: 0,
        uploadId,
        size: file.file.size,
        sizeUploaded: 0,
        proccessed: false,
        chunkId: uuidv4(),
      };

      filesData.push(chunk);
    }
  });
  return {
    totalSize,
    filesData,
    lastChunks,
    totalFiles: files.length,
    uploadedSize: 0,
    uploadedSizeFiles: 0,
  };
};

/**
* Gets the next chunk that has not been proccessed
* @param {Object} filesData
*
* @return {Object}
*/
const getFileToUpload = filesData => filesData.filter(file => !file.proccessed)[0];

/**
* Gets next chunk out of the queue for upload
* @param {Object} files
*
* @return {Object}
*/
const chunkForWorkQueue = (filesData) => {
  const file = getFileToUpload(filesData);

  if (file) {
    file.proccessed = true;
  }

  return { file };
};

/**
* Finds the chunks that failed more than 3 attmepts
* @param {Object} deadLetter
*
* @return {Array:[String]}
*/
const getDeadLetterFailures = (deadLetter) => {
  const failures = Object.keys(deadLetter).filter((key) => {
    return (deadLetter[key].attempts > 3);
  });

  const failureFileNames = failures.map((key) => {
    return deadLetter[key].chunk.file.entry.fullPath
  });

  return failureFileNames;
};

/**
* matches type to the mutation
* @param {string} connection
*
* @return {string}
*/
const getType = (connection) => {
  let type = '';

  switch (connection) {
    case 'DataBrowser_allFiles':
      type = 'addDatasetFile';
      break;
    case 'ImportLabbookMutation':
      type = 'importLabbook';
      break;
    case 'ImportDatasetMutation':
      type = 'importDataset';
      break;
    case 'Secrets_secretsFileMapping':
      type = 'uploadSecretsFile';
      break;
    default:
      type = 'addLabbookFile';
  }

  return type;
};

/**
* Multhithread uploader that handles file uploading
* @class
*/
export default class MultithreadUploader {
  constructor(config) {
    this.files = config.files;
    this.path = config.path;
    this.transactionId = uuidv4();
    this.uploadData = configureUploadData(config, this.transactionId);
    this.type = getType(config.mutationData.connection);
    this.component = config.component;

    this.mutationData = config.mutationData;

    this.chunksUploaded = 0;

    this.maxThreads = config.maxThreads || 4;
    this.chunkSize = chunkSize;
    this.status = 'available'; // available / uploading / paused

    this.workQueue = [];
    this.inFlight = [];
    this.deadLetter = {};
  }

  /**
  * Returns data about the file upload
  * @param {Array} files
  *
  * @return {}
  */
  startUpload(finishedCallback) {
    const { files } = this;
    this.initWorkQueue(files);

    this.finishedCallback = finishedCallback;
  }

  /**
  * Initiates upload by adding to workQueue and then adding to inFlight
  * @param {}
  * @fires addToWorkQueue
  * @fires addToInflight
  *
  * @return {}
  */
  initWorkQueue() {
    const workQueueMaxLength = (this.maxThreads * 4);
    for (let i = 0; i < workQueueMaxLength; i += 1) {
      this.addToWorkQueue();
    }

    for (let i = 0; i < this.maxThreads; i += 1) {
      this.addToInflight();
    }
  }

  /**
  * Concatonates the last chunks to the queue to be processed
  * @param {}
  * @fires initWorkQueue
  *
  * @return {}
  */
  uploadLastChunks() {
    this.uploadData.filesData = this.uploadData.filesData.concat(this.uploadData.lastChunks);
    this.uploadData.lastChunks = [];
    this.initWorkQueue();
  }

  /**
  * Gets chunks from filesData array
  * places chunk at the start of the queue
  * @param {} files
  * @fires chunkForWorkQueue
  *
  * @return {}
  */
  addToWorkQueue() {
    const chunk = chunkForWorkQueue(this.uploadData.filesData);

    if (chunk.file) {
      this.workQueue.unshift(chunk);
    }
  }

  /**
  * Checks if inFlight is less than 5
  * pops chunk from work queue and pushes chunk into in Flight
  * calls addToWorkQueue to get another chunk
  * @param {} files
  * @fires pushToInflight
  * @fires addToWorkQueue
  *
  * @return {}
  */
  addToInflight() {
    const inFlightLength = this.inFlight.length;

    if (inFlightLength < 5) {
      const chunk = this.workQueue.pop();
      if (chunk) {
        this.pushToInflight(chunk);
        this.addToWorkQueue();
      }
    }
  }

  /**
  * Gets matching completed chunk in the inflight and removes it from the array
  * calls continueUploa
  * @param {string} chunkId
  * @param {Boolean} isDeadLetter
  * @fires continueUpload
  *
  * @return {}
  */
  removeFromInflight(chunkId, isDeadLetter) {
    let index = 0;

    this.inFlight.forEach((chunk, chunkIndex) => {
      if (chunk.file.chunkId === chunkId) {
        index = chunkIndex;
      }
    });

    this.inFlight.splice(index, 1);

    if (!isDeadLetter) {
      this.continueUpload();
    }
  }

  /**
  * Decideds if upload continues or to complete
  * calls addToInflight
  * completes batchUplaod if workqueue and inFlight are empty
  * @param {}
  * @fires addToInflight
  * @fires completeUpload
  *
  * @return {}
  */
  continueUpload() {
    if (this.workQueue.length > 0) {
      this.addToInflight();
    }

    // check if there are any remaining chunks to upload
    if ((this.workQueue.length === 0) && (this.inFlight.length === 0)) {

      if (this.uploadData.lastChunks.length > 0) {
        this.uploadLastChunks();
      } else {
        this.completeUpload();
      }
    }
  }

  /**
  * Pushes chunk to inflight and starts worker to upload file
  * @param {object} chunk
  * @fires removeFromInflight
  * @fires setUploadMessageUpdate
  *
  * @return {}
  */
  pushToInflight(chunk) {
    const worker = new Worker('./UploadWorker.js', { type: 'module' });
    this.inFlight.push(chunk);

    worker.onmessage = (evt) => {
      const { data } = evt;
      const { response } = data;
      if (response[this.type]) {
        const fileType = this.type === 'addLabbookFile' ? 'newLabbookFileEdge' : 'newDatasetFileEdge';
        const secretsType = this.type === 'uploadSecretsFile';
        if (response[this.type]
          && response[this.type][fileType]
          && response[this.type][fileType].node) {
          UpdateFileBrowserStore.insertFileBrowserEdge(
            response[this.type][fileType],
            this.mutationData,
            this.component,
          );
        } else if (response[this.type]
          && secretsType) {
          UpdateSecretsStore.insertSecretsEdge(
            response[this.type].environment.secretsFileMapping.edges,
            this.mutationData,
            this.component,
          );
        }

        this.chunksUploaded += 1;
        const totalChunks = (this.uploadData.filesData.length + this.uploadData.lastChunks.length);
        const percentage = (this.chunksUploaded / totalChunks) * 100;
        const prettyPercentage = percentage.toFixed(0);
        const totalFiles = this.files.length;

        setUploadMessageUpdate(
          `Uploading ${totalFiles} files, ${prettyPercentage}% complete`,
          this.chunksUploaded,
          percentage,
        );
        if (response[this.type].importJobKey !== null) {
          this.importJobKey = response[this.type].importJobKey;
        }

        this.removeFromInflight(data.chunkId, false);
      } else {
        this.addToDeadLetter(chunk);
      }

      worker.terminate();
    };

    worker.onerror = () => {
      this.addToDeadLetter(chunk);
      worker.terminate();
    };

    worker.postMessage(chunk);
  }

  /**
  * Adds count on dead letter and allows 3 attempts at upload per failed chunk
  * @param {object} chunk
  * @fires removeFromInflight
  * @fires pushToInflight
  *
  * @return {}
  */
  addToDeadLetter(chunk) {
    const chunkName = chunk.file.file.entry.fullPath + chunk.file.chunkIndex;

    if (this.deadLetter[chunkName]) {
      const { failedAttempts } = this.deadLetter[chunkName];

      if (failedAttempts < 4) {
        this.deadLetter[chunkName].failedAttempts += 1;
        this.removeFromInflight(chunk.transactionId, true);
        this.pushToInflight(chunk);
      } else {
        this.addToWorkQueue();
        this.removeFromInflight(chunk.transactionId, false);
      }
    } else {
      this.removeFromInflight(chunk.transactionId, true);
      this.deadLetter[chunkName] = {
        failedAttempts: 1,
        chunk,
      };
      this.pushToInflight(chunk);
    }
  }

  /**
  * Pushes chunk to inflight and starts worker to upload file
  * @param {}
  * @fires CompleteDatasetUploadTransactionMutation
  * @fires CompleteBatchUploadTransactionMutation
  *
  * @return {}
  */
  completeUpload = () => {
    const {
      owner,
      name,
      connection,
    } = this.mutationData;
    const callback = (response, error) => {
      const totalFiles = this.uploadData.filesData.length;

      if (connection !== 'DataBrowser_allFiles') {
        setUploadMessageRemove(`Uploaded ${totalFiles} files. Please wait while upload is finalizing.`, null, 100);
        this.finishedCallback();
      }

      if (response && response.completeDatasetUploadTransaction) {
        FooterUtils.datasetUploadStatus(
          response,
          this.finishedCallback,
          {
            owner,
            name,
          },
        );
      }

      if (error) {
        setErrorMessage('Upload failed: ', error);
      }
    };

    if (connection.indexOf('_allFiles') > -1) {
      if (connection === 'DataBrowser_allFiles') {
        CompleteDatasetUploadTransactionMutation(
          connection,
          owner,
          name,
          false,
          false,
          this.transactionId,
          callback,
        );
      } else {
        CompleteBatchUploadTransactionMutation(
          connection,
          owner,
          name,
          false,
          false,
          this.transactionId,
          callback,
        );

        // setFinishedUploading();
      }
    } else if (connection === 'Secrets_secretsFileMapping') {
      callback();
      setTimeout(() => {
        setUploadMessageRemove('Completed Upload', null, 100);
      }, 1000);
    } else {
      const { importJobKey } = this;
      if (importJobKey) {
        const footerData = {
          result: { [this.type]: { importJobKey } },
          type: this.type,
          key: 'importJobKey',
          callback: this.finishedCallback,
        };
        FooterUtils.getJobStatus(owner, labbookName, footerData);
      }
    }

    const failures = getDeadLetterFailures(this.deadLetter);

    if (failures.length > 0) {
      const failureString = failures.join(', ');
      setErrorMessage({ message: `Failed to upload the following files: ${failureString}` });
    }
  }
}
