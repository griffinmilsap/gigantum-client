// mutations
import DeleteLabbookFilesMutation from 'Mutations/fileBrowser/DeleteLabbookFilesMutation';
import DeleteDatasetFilesMutation from 'Mutations/fileBrowser/DeleteDatasetFilesMutation';
import MakeLabbookDirectoryMutation from 'Mutations/fileBrowser/MakeLabbookDirectoryMutation';
import MakeDatasetDirectoryMutation from 'Mutations/fileBrowser/MakeDatasetDirectoryMutation';
import MoveLabbookFileMutation from 'Mutations/fileBrowser/MoveLabbookFileMutation';
import MoveDatasetFileMutation from 'Mutations/fileBrowser/MoveDatasetFileMutation';
import DownloadDatasetFilesMutation from 'Mutations/DownloadDatasetFilesMutation';
import CompleteBatchUploadTransactionMutation from 'Mutations/fileBrowser/CompleteBatchUploadTransactionMutation';
import UpdateUnmanagedDatasetMutation from 'Mutations/UpdateUnmanagedDatasetMutation';
import VerifyDatasetMutation from 'Mutations/VerifyDatasetMutation';
// store
import store from 'JS/redux/store';
import { setErrorMessage } from 'JS/redux/actions/footer';
import { setIsProcessing } from 'JS/redux/actions/dataset/dataset';

class FileBrowserMutations {
  /**
    * @param {Object} props
    *        {string} props.owner
    *        {string} props.name
    *        {string} props.section
    *        {string} props.connection
    *        {string} props.favoriteConnection
    *        {string} props.parentId
    * pass above props to state
    */
  constructor(props) {
    this.state = props;
  }

  downloadDatasetFiles(data, callback) {
    const {
      keys,
      allKeys,
      owner,
      datasetName,
      labbookName,
      labbookOwner,
      successCall,
      failureCall,
    } = data;

    DownloadDatasetFilesMutation(
      owner,
      datasetName,
      labbookName,
      labbookOwner,
      successCall,
      failureCall,
      keys,
      allKeys,
      callback,
    );
  }

  /**
   *  @param {Object} data
   *         {string} data.key
   *  @param {function} callback
   *  creates a dirctory using MakeLabbookDirectoryMutation
   */
  makeLabbookDirectory(data, callback) {
    const {
      key,
    } = data;

    const {
      connection,
      owner,
      name,
      parentId,
      section,
    } = this.state;
    if (section !== 'data') {
      MakeLabbookDirectoryMutation(
        connection,
        owner,
        name,
        parentId,
        key,
        section,
        (response, error) => {
          if (error) {
            console.error(error);
            setErrorMessage(owner, name, `ERROR: could not create ${key}`, error);
          }
          callback(response, error);
        },
      );
    } else {
      setIsProcessing(owner, name, true);
      MakeDatasetDirectoryMutation(
        connection,
        owner,
        name,
        parentId,
        `${key}/`,
        (response, error) => {
          if (error) {
            console.error(error);
            setErrorMessage(owner, name, `ERROR: could not create ${key}`, error);
          }
          setTimeout(() => setIsProcessing(owner, name, false), 1100);
          callback(response, error);
        },
      );
    }
  }

  /**
   *  @param {Object} data
   *         {string} data.newKey
   *         {Object} data.edge
   *         {Array[string]} data.removeIds
   *  @param {function} callback
   *  moves file from old folder to a new folder
   */
  moveDatasetFile(data, callback) {
    const {
      edge,
      newKey,
      removeIds,
    } = data;

    const {
      connection,
      owner,
      name,
      section,
      parentId,
    } = this.state;

    const { key } = edge.node;

    setIsProcessing(owner, name, true);
    MoveDatasetFileMutation(
      connection,
      owner,
      name,
      parentId,
      edge,
      key,
      newKey,
      section,
      removeIds,
      (response, error) => {
        setTimeout(() => setIsProcessing(owner, name, false), 1100);
        callback(response, error);
      },
    );
  }

  /**
   *  @param {Object} data
   *         {string} data.newKey
   *         {Object} data.edge
   *         {Array[string]} data.removeIds
   *  @param {function} callback
   *  moves file from old folder to a new folder
   */
  moveLabbookFile(data, callback) {
    const {
      edge,
      newKey,
      removeIds,
    } = data;

    const {
      connection,
      owner,
      name,
      section,
      parentId,
    } = this.state;

    const { key } = edge.node;

    MoveLabbookFileMutation(
      connection,
      owner,
      name,
      parentId,
      edge,
      key,
      newKey,
      section,
      removeIds,
      (response, error) => {
        callback(response, error);
      },
    );
  }

  /**
  *  @param {Object} data
  *         {Array[string]} data.filePaths
  *         {Array[Object]} data.edges
  *  @param {function} callback
  *  remove file or folder from directory
  */
  deleteLabbookFiles(data, callback) {
    const {
      filePaths,
      edges,
    } = data;
    const {
      connection,
      owner,
      name,
      parentId,
      section,
    } = this.state;

    if (section !== 'data') {
      DeleteLabbookFilesMutation(
        connection,
        owner,
        name,
        parentId,
        filePaths,
        section,
        edges,
        (response, error) => {
          if (error) {
            console.error(error);
            const keys = filePaths.join(' ');
            setErrorMessage(owner, name, `ERROR: could not delete folders ${keys}`, error);
          }
        },
      );
    } else {
      setIsProcessing(owner, name, true);

      DeleteDatasetFilesMutation(
        connection,
        owner,
        name,
        parentId,
        filePaths,
        section,
        edges,
        (response, error) => {
          if (error) {
            console.error(error);
            const keys = filePaths.join(' ');
            setErrorMessage(owner, name, `ERROR: could not delete folders ${keys}`, error);
          }
          setTimeout(() => setIsProcessing(owner, name, false), 1100);
        },
      );
    }
  }

  /**
  *  @param {undefined} data
  *  @param {function} callback
  *  remove file from favorite section
  */
  completeBatchUploadTransaction(data, callback) {
    const {
      connection,
      owner,
      name,
    } = this.state;
    const { transactionId } = store.getState().fileBrowser;
    CompleteBatchUploadTransactionMutation(
      connection,
      owner,
      name,
      true,
      false,
      transactionId,
      () => {},
    );
  }


  /**
  *  @param {undefined} data
  *  @param {function} callback
  *  updates unmanaged dataset
  */
  updateUnmanagedDataset(data, callback) {
    const {
      owner,
      name,
    } = this.state;

    const {
      fromLocal,
      fromRemote,
    } = data;

    UpdateUnmanagedDatasetMutation(
      owner,
      name,
      fromLocal,
      fromRemote,
      callback,
    );
  }

  /**
  *  @param {undefined} data
  *  @param {function} callback
  *  verifies unmanaged dataset
  */
  verifyDataset(data, callback) {
    const {
      owner,
      name,
    } = this.state;

    VerifyDatasetMutation(
      owner,
      name,
      (response, error) => {},
    );
  }
}

export default FileBrowserMutations;
