// vendor
import uuidv4 from 'uuid/v4';
// store
import {
  setUploadMessageUpdate,
  setUploadMessageRemove,
  setWarningMessage,
} from 'JS/redux/actions/footer';
import {
  setFileBrowserLock,
} from 'JS/redux/actions/labbook/labbook';
// utils
import MutlithreadUploader from 'JS/utils/MultithreadUploader';

/**
  * @param {object} file
  * @param {string} typeOfUpload
  * @param {function} buildImage
  * @param {object} state
  * @param {object} history
  * starts upload process and triggers import
  *
  * @return {array}
*/
const prepareUpload = (mutationData, component) => {
  const {
    file,
    typeOfUpload,
    owner,
    name,
    environmentId,
    id,
    filename,
  } = mutationData;
  const newFileArray = [
    {
      file,
      entry: {
        fullPath: file.name,
        name: file.name,
      },
    },
  ];


  const uploadInstance = new MutlithreadUploader({
    files: newFileArray,
    path: '',
    mutationData: {
      connection: typeOfUpload,
      owner,
      name,
      environmentId,
      id,
      filename,
    },
    maxThreads: 4,
    component,
    refetch: () => {},
  });


  /**
    * @param {object} evt
    * function to warn user on reload or navigating away from the user
    *
    * @return {array}
  */
  const navigateConfirm = (evt) => {
    evt.preventDefault();
    evt.returnValue = '';
    return '';
  };

  /**
    * @param {object} response
    * triggers when upolad has finished
    * builds image and redirects to new project
    *
    * @return {array}
  */
  const finishedCallback = (response) => {
    window.removeEventListener('beforeunload', navigateConfirm);
    setFileBrowserLock(false);
    setUploadMessageRemove('Completed Upload');
  };

  window.addEventListener('beforeunload', navigateConfirm);
  uploadInstance.startUpload(finishedCallback);

  setFileBrowserLock(true);
  setUploadMessageUpdate('Storing secret file, 0% complete');
};

export default prepareUpload;
