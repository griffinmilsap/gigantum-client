import tips from './tips';

const CONFIG = {
  api: process.env.NODE_ENV,
  domain: 'gigantum.io',
  labbook_navigation_items: [
    { id: 'overview', name: 'Overview' },
    { id: 'activity', name: 'Activity', fragment: '...Activity_labbook' },
    { id: 'environment', name: 'Environment', fragment: '...Environment_labbook' },
    { id: 'code', name: 'Code' },
    { id: 'inputData', name: 'Input Data' },
    { id: 'outputData', name: 'Output Data' },
  ],
  dataset_navigation_items: [
    { id: 'overview', name: 'Overview' },
    { id: 'activity', name: 'Activity', fragment: '...Activity_labbook' },
    { id: 'data', name: 'Data' },
  ],
  labbookDefaultNavOrder: ['overview', 'activity', 'environment', 'code', 'inputData', 'outputData'],
  datasetDefaultNavOrder: ['activity', 'data'],
  navTitles: {
    overview: 'A brief overview of the Project',
    activity: 'Lists activity records for the Project',
    environment: 'View and modify packages and docker instructions',
    code: 'View and modify code files',
    inputData: 'View and modify input data files',
    outputData: 'View and modify output data files',
  },
  modalNav: [
    { id: 'createLabook', description: 'Title & Description' },
    { id: 'selectBaseImage', description: 'Base Image' },
    { id: 'selectDevelopmentEnvironment', description: 'Dev Environment' },
    { id: 'addEnvironmentPackage', description: 'Add Dependencies' },
    { id: 'successMessage', description: 'Success' },
  ],
  months: [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ],
  fileBrowser: {
    excludedFiles: [
      'DS_Store',
      'zip',
      'lbk',
      'pyc',
      'gitkeep',
    ],
  },

  containerStatus: {
    canEditEnvironment: status => (status === 'Stopped') || (status === 'Rebuild'),
  },
  userAPI: {
    getUsersQueryString: (userInput) => {
      const sanitizedUserInput = userInput.replace(/-/g, ' ');
      const apiURL = `https://m9eq4m3z0f.execute-api.us-east-1.amazonaws.com/prod?q=${sanitizedUserInput}*&q.options={fields: ['username^5','name']}&size=10`;

      return encodeURI(apiURL);
    },
    getUserEmailQueryString: (email) => {
      const apiURL = `https://m9eq4m3z0f.execute-api.us-east-1.amazonaws.com/prod?q=${email}&q.options={fields: ['email']}&size=10`;

      return encodeURI(apiURL);
    },
  },
  getTooltipText: section => tips[section],
  demoHostName: 'try.gigantum.com',
  /**
    @param {number} bytes
    converts bytes into suitable units
  */
  humanFileSize: (bytes) => {
    const si = true;
    const thresh = si ? 1000 : 1024;
    if (Math.abs(bytes) < thresh) {
      return `${bytes}B`;
    }
    const units = si
      ? ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
      : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
    let u = -1;
    do {
      bytes /= thresh;
      ++u;
    } while (Math.abs(bytes) >= thresh && u < units.length - 1);
    return `${bytes.toFixed(1)} ${units[u]}`;
  },
};

export default CONFIG;
