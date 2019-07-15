// vendor
import config from 'JS/config';
// store
import {
  setUploadMessageUpdate,
  setWarningMessage,
} from 'JS/redux/actions/footer';
import {
  setFileBrowserLock,
} from 'JS/redux/actions/labbook/labbook';
// utils
import MutlithreadUploader from 'JS/utils/MultithreadUploader';
/**
* Removes files that are not allowed to be uploaded to gigantum.
* @param {Array} files
*
* @return {Array}
*/
const removeExcludedFiles = (files) => {
  const filesNotAllowedList = [];
  const newFileArray = files.filter((fileItem) => {
    const extension = fileItem.file.name
      ? fileItem.file.name.replace(/.*\./, '')
      : fileItem.entry.fullPath.replace(/.*\./, '');
    const fileAllowed = (config.fileBrowser.excludedFiles.indexOf(extension) < 0);

    if (!fileAllowed) {
      filesNotAllowedList.push(fileItem.file.name);
    }

    return fileAllowed;
  });


  if (filesNotAllowedList.length > 0) {
    const filesNotAllowed = filesNotAllowedList.join(', ');
    setWarningMessage(`The following files are not allowed ${filesNotAllowed}`);
  }

  return newFileArray;
};


/**
* @param {Array} files
*
* @return {Array}
*/
const flattenFiles = (files) => {
  const flattenedFiles = [];

  /**
  * Runs recursively to flatten file upload array
  * @param {Array} files
  */
  function recursiveFlatten(filesArray) {
    if (Array.isArray(filesArray)) {
      filesArray.forEach((filesSubArray) => {
        recursiveFlatten(filesSubArray);
      });
    } else if (Array.isArray(filesArray.file) && (filesArray.file.length > 0)) {
      recursiveFlatten(filesArray.file);
    } else if (filesArray.entry) {
      flattenedFiles.push({
        file: filesArray.file,
        entry: {
          fullPath: filesArray.entry.fullPath,
          name: filesArray.entry.name,
        },
      });
    } else {
      flattenedFiles.push({
        file: filesArray,
        entry: {
          fullPath: filesArray.name,
          name: filesArray.name,
        },
      });
    }
  }

  recursiveFlatten(files);

  const prunedFiles = removeExcludedFiles(flattenedFiles);
  return prunedFiles;
};

/**
* @param {Array:[Object]} files
* @param {String} promptType
*
* @return {number} totalFiles
*/
const checkFileSize = (files, promptType) => {
  const tenMB = 10 * 1000 * 1000;
  const oneHundredMB = 10 * tenMB;
  const fiveHundredMB = oneHundredMB * 5;
  const fifteenGigs = oneHundredMB * 150;
  const filesAllowed = [];
  const fileSizePrompt = [];
  const fileSizeNotAllowed = [];
  let index = 0;

  function filesRecursionCount(file) {
    const fileSize = file.file.size;
    if (promptType === 'CodeBrowser_allFiles') {
      if (fileSize > oneHundredMB) {
        fileSizeNotAllowed.push(file);
      } else if ((fileSize > tenMB) && (fileSize < oneHundredMB)) {
        fileSizePrompt.push(file);
      } else {
        filesAllowed.push(file);
      }
    } else if ((promptType === 'InputBrowser_allFiles') || (promptType === 'OutputBrowser_allFiles')) {
      if (fileSize > fiveHundredMB) {
        fileSizeNotAllowed.push(file);
      } else if ((fileSize > oneHundredMB) && (fileSize < fiveHundredMB)) {
        fileSizePrompt.push(file);
      } else {
        filesAllowed.push(file);
      }
    } else if (promptType === 'DataBrowser_allFiles') {
      if (fileSize > fifteenGigs) {
        fileSizeNotAllowed.push(file);
      } else {
        filesAllowed.push(file);
      }
    }

    index += 1;
    if (files[index]) {
      filesRecursionCount(files[index]);
    }
  }
  filesRecursionCount(files[index]);

  return { fileSizeNotAllowed, fileSizePrompt, filesAllowed };
};

const uploadDirContent = (dndItem, props, monitor, callback) => {
  let path;

  dndItem.dirContent.then((fileList) => {

    if (fileList.length > 0) {
      const files = flattenFiles(fileList);
      let key = props.fileData ? props.fileData.edge.node.key : '';
      key = props.fileKey ? props.fileKey : key;
      path = key === '' ? '' : key.substr(0, key.lastIndexOf('/') || key.length);

      callback(files, `${path}/`);
    } else if (dndItem.files && dndItem.files.length) {
      // handle dragged files
      const item = monitor.getItem();
      const key = props.newKey || props.fileKey;
      path = key.substr(0, key.lastIndexOf('/') || key.length);

      if (item && item.files && props.browserProps.createFiles) {
        const files = flattenFiles(item.files);
        callback(files, `${path}/`);
      }
    }
  });
};


/**
* @param {Array:[Object]} files
* @param {String} path
* @param {Object} mutationData
* @param {JSX} component
*
* @return {number} totalFiles
*/
const handleCallback = (filesTemp, path, mutationData, component) => {
  if (filesTemp.length > 0) {
    const fileSizeData = checkFileSize(filesTemp, mutationData.connection);

    const uploadCallback = (fileData) => {
      if (fileSizeData.fileSizeNotAllowed.length > 0) {
        const fileToolarge = fileSizeData.fileSizeNotAllowed.map(file => file.entry.fullPath);
        const fileListAsString = fileToolarge.join(', ');
        setWarningMessage(`The following files are too large to upload to this section ${fileListAsString}`);
      } else {
        const navigateConfirm = (evt) => {
          evt.preventDefault();
          evt.returnValue = '';
          return '';
        };

        const finishedCallback = () => {
          window.removeEventListener('beforeunload', navigateConfirm);
          setFileBrowserLock(false);
        };

        const uploadInstance = new MutlithreadUploader({
          files: fileData.filesAllowed,
          path,
          mutationData,
          maxThreads: 4,
          component,
        });

        window.addEventListener('beforeunload', navigateConfirm);
        uploadInstance.startUpload(finishedCallback);
        setFileBrowserLock(true);
        setUploadMessageUpdate(`Uploading ${fileData.filesAllowed.length} files, 0% complete`);
      }
    };

    if (fileSizeData.fileSizePrompt.length > 0) {
      if (component._fileSizePrompt) {
        component._fileSizePrompt(fileSizeData, uploadCallback);
      } else {
        component.props.fileSizePrompt(fileSizeData, uploadCallback);
      }
    } else {
      uploadCallback(fileSizeData);
    }
  }
};


/**
* formats files for upload
* @param {Object} dndItem
* @param {function} setCallbackRoute
*
* @calls {callback}
*/
const uploadFromFileSelector = (dndItem, callback) => {
  const files = dndItem.map(item => ({
    file: item,
    entry: {
      fullPath: item.name,
      name: item.name,
    },
  }));


  callback(files);
};

/**
* @param {Object} dndItem
* @param {Object} props
* @param {Object} monitor
* @param {Object} mutationData
* @param {JSX} component
*
* @return {number} totalFiles
*/
const prepareUpload = (dndItem, props, monitor, mutationData, component) => {
  if (dndItem.dirContent) {
    const callback = (filesTemp, path) => {
      handleCallback(filesTemp, path, mutationData, component);
    };

    uploadDirContent(dndItem, props, monitor, callback);
  } else {
    const callback = (filesTemp) => {
      handleCallback(filesTemp, '', mutationData, component);
    };
    uploadFromFileSelector(dndItem, callback);
  }
};
export default prepareUpload;
