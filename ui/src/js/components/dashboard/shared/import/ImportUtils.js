// vendor
import uuidv4 from 'uuid/v4';
// store
import store from 'JS/redux/store';
import { setUploadMessageRemove } from 'JS/redux/actions/footer';
// config
import config from 'JS/config';

/**
 @param {object} workerData
 uses redux to dispatch file upload to the footer
*/
const dispatchLoadingProgress = (wokerData) => {
  let bytesUploaded = (wokerData.chunkSize * (wokerData.chunkIndex + 1));
  const totalBytes = wokerData.fileSize;
  bytesUploaded = bytesUploaded < totalBytes
    ? bytesUploaded
    : totalBytes;
  const totalBytesString = config.humanFileSize(totalBytes);
  const bytesUploadedString = config.humanFileSize(bytesUploaded);

  store.dispatch({
    type: 'UPLOAD_MESSAGE_UPDATE',
    payload: {
      id: '',
      uploadMessage: `${bytesUploadedString} of ${totalBytesString} uploaded`,
      totalBytes,
      percentage: (Math.floor((bytesUploaded / totalBytes) * 100) <= 100)
        ? Math.floor((bytesUploaded / totalBytes) * 100)
        : 100,
    },
  });

  if (document.getElementById('footerProgressBar')) {
    const width = Math.floor((bytesUploaded / totalBytes) * 100);
    document.getElementById('footerProgressBar').style.width = `${width}%`;
  }
};

/**
 @param {} -
 uses redux to dispatch file upload failed status to the footer
*/
const dispatchFailedStatus = () => {
  store.dispatch({
    type: 'UPLOAD_MESSAGE_UPDATE',
    payload: {
      uploadMessage: 'Import failed',
      id: '',
      percentage: 0,
      uploadError: true,
    },
  });
};

/**
 @param {string} filePath
  gets new labbook name and url route
 @return
*/
const getRoute = (filepath) => {
  const filename = filepath.split('/')[filepath.split('/').length - 1];
  return filename.split('_')[0];
};
/**
 @param {string} filePath
 dispatched upload success message and passes labbookName/route to the footer
*/
const dispatchFinishedStatus = (filepath, props, buildImage) => {
  const route = getRoute(filepath);
  const root = props.section === 'labbook' ? 'projects' : 'datasets';
  props.history.push(`/${root}/${localStorage.getItem('username')}/${route}`);

  if (props.section === 'labbook') {
    buildImage(route, localStorage.getItem('username'), uuidv4());
  }
  setUploadMessageRemove('', uuidv4(), 0);
};


export default {
  dispatchLoadingProgress,
  dispatchFailedStatus,
  getRoute,
  dispatchFinishedStatus,
};
