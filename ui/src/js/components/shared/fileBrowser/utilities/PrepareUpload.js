// vendor
import config from 'JS/config';
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
* Updates redux store to clear loading data.
* @param {String} owner
* @param {String} name
*
* @return {}
*/
const clearFileUpload = (owner, name) => {
  setUploadMessageRemove('', null, 0);
  setWarningMessage(owner, name, 'All provided file types are not allowed or the provided directory is empty. Verify selection and try again.');
  setFileBrowserLock(owner, name, false);
};


/**
* Returns section and fileSize limit for given section
* @param {Object} mutationData
*
* @return {}
*/
const getSectionLimit = (mutationData) => {
  const { section } = mutationData;
  const sectionText = section.charAt(0).toUpperCase() + section.slice(1, section.length);

  if (section === 'code') {
    const fileSizeLimit = '100MB';
    return { section: sectionText, fileSizeLimit };
  }

  if ((section === 'input') || (section === 'output')) {
    const fileSizeLimit = '500MB';
    const sectionTextComplete = `${sectionText} Data`;
    return { section: sectionTextComplete, fileSizeLimit };
  }

  const fileSizeLimit = '15GB';
  return { section: sectionText, fileSizeLimit };
};

/**
* Removes files that are not allowed to be uploaded to gigantum.
* @param {Array} files
*
* @return {Array}
*/
const removeExcludedFiles = (files, owner, name) => {
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
    setWarningMessage(owner, name, `The following files are not allowed ${filesNotAllowed}`);
  }

  return newFileArray;
};


/**
* @param {Array} files
*
* @return {Array}
*/
const flattenFiles = (files, owner, name) => {
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
      if (!Array.isArray(filesArray.file)
        || ((Array.isArray(filesArray.file))
        && (filesArray.file.length > 0))
      ) {
        flattenedFiles.push({
          file: filesArray.file,
          entry: {
            fullPath: filesArray.entry.fullPath,
            name: filesArray.entry.name,
          },
        });
      }
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

  const prunedFiles = removeExcludedFiles(flattenedFiles, owner, name);

  if (prunedFiles.length === 0) {
    clearFileUpload(owner, name);
  }
  return prunedFiles;
};

/**
* @param {Array:[Object]} files
* @param {String} promptType
*
* @return {number} totalFiles
*/
const checkFileSize = (files, promptType, owner, labbookName) => {
  const tenMB = 10 * 1000 * 1000;
  const oneHundredMB = 10 * tenMB;
  const fiveHundredMB = oneHundredMB * 5;
  const fifteenGigs = oneHundredMB * 150;
  const filesAllowed = [];
  const fileSizePrompt = [];
  const fileSizeNotAllowed = [];
  let index = 0;

  if (files.length > 10000) {
    setFileBrowserLock(owner, labbookName, true);
    return {
      fileSizeNotAllowed,
      fileSizePrompt,
      filesAllowed,
      tooManyFiles: true,
    };
  }

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
      try {
        filesRecursionCount(files[index]);
      } catch (error) {
        console.log(error);
      }
    }
  }
  filesRecursionCount(files[index]);

  return {
    fileSizeNotAllowed,
    fileSizePrompt,
    filesAllowed,
    tooManyFiles: false,
  };
};

const uploadDirContent = (dndItem, props, monitor, callback, mutationData) => {
  let path;

  const {
    owner,
    labbookName,
  } = mutationData;

  dndItem.dirContent.then((fileList) => {
    if (fileList.length > 0) {
      const files = flattenFiles(fileList, owner, labbookName);
      let key = props.fileData ? props.fileData.edge.node.key : '';
      key = props.fileKey ? props.fileKey : key;
      path = key === '' ? '' : key.substr(0, key.lastIndexOf('/') || key.length);
      callback(files, `${path}/`);
    } else if (dndItem.files && dndItem.files.length) {
      // handle dragged files
      const item = monitor.getItem();
      const key = props.newKey || props.fileKey;
      if (key) {
        path = key.substr(0, key.lastIndexOf('/') || key.length);
      }

      if (item && item.files && props.browserProps.createFiles) {
        const files = flattenFiles(item.files, owner, labbookName);
        callback(files, `${path}/`);
      } else {
        clearFileUpload(owner, labbookName);
      }
    } else {
      clearFileUpload(owner, labbookName);
    }
  });
};


/**
* @param {Array:[Object]} files
* @param {String} path
* @param {Object} mutationData
* @param {React.Node} component
*
* @return {number} totalFiles
*/
const handleCallback = (filesTemp, path, mutationData, component) => {
  const {
    labbookName,
    owner,
  } = mutationData;

  if (filesTemp.length > 0) {
    const fileSizeData = checkFileSize(filesTemp, mutationData.connection, owner, labbookName);

    if (fileSizeData.tooManyFiles) {
      setUploadMessageRemove('Too many files', null, 0);
      setWarningMessage(owner, labbookName, 'Exceeded upload limit, up to 10,000 files can be uploaded at once');
      setFileBrowserLock(owner, labbookName, false);
      return;
    }

    const uploadCallback = (fileData) => {
      if (fileSizeData.fileSizeNotAllowed.length > 0) {
        const fileToolarge = fileSizeData.fileSizeNotAllowed.map(file => file.entry.fullPath);
        const fileListAsString = fileToolarge.join(', ');
        const { section, fileSizeLimit } = getSectionLimit(mutationData);
        setWarningMessage(owner, labbookName, `The following files are too large to upload to this section ${fileListAsString}, ${section} has a limit of ${fileSizeLimit}`);
      }

      if (fileSizeData.filesAllowed.length > 0) {
        const navigateConfirm = (evt) => {
          evt.preventDefault();
          evt.returnValue = '';
          return '';
        };

        const finishedCallback = () => {
          window.removeEventListener('beforeunload', navigateConfirm);
          setFileBrowserLock(owner, labbookName, false);
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
        setFileBrowserLock(owner, labbookName, true);
        setUploadMessageUpdate(`Uploading ${fileData.filesAllowed.length} files, 0% complete`);
      } else {
        setUploadMessageRemove('', null, 0);
        setFileBrowserLock(owner, labbookName, false);
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
  } else {
    clearFileUpload(owner, labbookName);
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
  const {
    labbookName,
    owner,
  } = mutationData;
  setFileBrowserLock(owner, labbookName, true);
  setUploadMessageUpdate('Preparing file upload');

  if (dndItem.dirContent) {
    const callback = (filesTemp, path) => {
      handleCallback(filesTemp, path, mutationData, component);
    };

    uploadDirContent(dndItem, props, monitor, callback, mutationData);
  } else {
    const callback = (filesTemp) => {
      handleCallback(filesTemp, '', mutationData, component);
    };
    uploadFromFileSelector(dndItem, callback);
  }
};
export default prepareUpload;
