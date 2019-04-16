import { combineReducers } from 'redux';
import footer from './reducers/footer';
import login from './reducers/login';
import routes from './reducers/routes';
import helper from './reducers/helper';
// labbook listing reducers
import labbookListing from './reducers/labbookListing/labbookListing';
// dataset listing reducers
import datasetListing from './reducers/datasetListing/datasetListing';
// dataset reducers
import dataset from './reducers/dataset/dataset';
// labbook reducers
import labbook from './reducers/labbook/labbook';
import containerStatus from './reducers/labbook/containerStatus';
// labbooks/overview reducers
import overview from './reducers/labbook/overview/overview';
// labbooks/environment reducers
import environment from './reducers/labbook/environment/environment';
import packageDependencies from './reducers/labbook/environment/packageDependencies';
// labbooks/fileBrowser reducers
import fileBrowser from './reducers/shared/fileBrowser/fileBrowserWrapper';
// labbooks/branchMenu/collaborators reducers
import collaborators from './reducers/shared/collaborators/collaborators';

export default combineReducers({
  footer,
  overview,
  labbook,
  routes,
  containerStatus,
  environment,
  packageDependencies,
  login,
  fileBrowser,
  collaborators,
  helper,
  labbookListing,
  datasetListing,
  dataset,
});
