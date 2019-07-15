// vendor
import { Provider } from 'react-redux';
import React from 'react';
import renderer from 'react-test-renderer';
import FileBrowserDropZone from 'Components/shared/fileBrowser/FileBrowser';
import { mount, shallow } from 'enzyme';
import { BrowserRouter as Router } from 'react-router-dom';
// import { Provider } from 'react-redux';
import store from 'JS/redux/store';
// fixtures
import Auth from 'JS/Auth/Auth';
import history from 'JS/history';
// data
import data from 'Tests/components/labbook/code/__relaydata__/MostRecentCode.json';
import codeData from 'Tests/components/labbook/code/__relaydata__/CodeBrowser.json';
import codeDataFavorites from 'Tests/components/labbook/code/__relaydata__/CodeFavorites.json';
// mutations
import DeleteLabbookFilesMutation from 'Mutations/fileBrowser/DeleteLabbookFilesMutation';
import MakeLabbookDirectoryMutation from 'Mutations/fileBrowser/MakeLabbookDirectoryMutation';
import MoveLabbookFileMutation from 'Mutations/fileBrowser/MoveLabbookFileMutation';
import DownloadDatasetFilesMutation from 'Mutations/DownloadDatasetFilesMutation';
import CompleteBatchUploadTransactionMutation from 'Mutations/fileBrowser/CompleteBatchUploadTransactionMutation';

const auth = new Auth();


const variables = { first: 20, labbook: 'ui-test-project' };
export default variables;

const { labbook } = codeData.data;

const setRootFolder = () => {};

const fixtures = {
  connectDropTarget: jsx => jsx,
  clearSelectedFiles: jest.fn(),
  loadStatus: jest.fn(),
  setRootFolder: jest.fn(),
  selectedFiles: [],
  labbookId: labbook.id,
  sectionId: labbook.code.id,
  section: 'code',
  isLocked: false,
  ...labbook.code,
  labbook,
  files: labbook.code.allFiles,
  parentId: labbook.id,
  connection: 'CodeBrowser_allFiles',
  favoriteConnection: 'CodeFavorites_favorites',
  favorites: codeDataFavorites.data.labbook.code.favorites,
};

jest.mock('Mutations/fileBrowser/DeleteLabbookFilesMutation', () => jest.fn());
jest.mock('Mutations/fileBrowser/MakeLabbookDirectoryMutation', () => jest.fn());
jest.mock('Mutations/fileBrowser/MoveLabbookFileMutation', () => jest.fn());
jest.mock('Mutations/DownloadDatasetFilesMutation', () => jest.fn());
jest.mock('Mutations/fileBrowser/CompleteBatchUploadTransactionMutation', () => jest.fn());


auth.isAuthenticated = function () { return true; };
const FileBrowser = FileBrowserDropZone.DecoratedComponent;

describe('FileBrowser component', () => {
  it('Test FileBrowser Rendering', () => {
        const component = renderer.create(<Provider store={store}><FileBrowserDropZone.DecoratedComponent
              {...fixtures}
            /></Provider>);

        let tree = component.toJSON();
        expect(tree).toMatchSnapshot();
   });

   const component = mount(<FileBrowserDropZone.DecoratedComponent {...fixtures } />);

   let deleteCount = 0;
   const MockFn = jest.fn();
   const mockDeleteMutation = new MockFn();
   component._deleteMutation = mockDeleteMutation;

   it('Sorts by date', () => {
     component.find('.FileBrowser__header--date').simulate('click');
     expect(component.state().sort).toEqual('modified');
   });

   it('Multiselect selects all', () => {
     component.find('.CheckboxMultiselect').simulate('click');
     expect(component.state('multiSelect')).toEqual('all');
   });

   it('Cancel delete popup', () => {
     component.find('.File__btn--delete').simulate('click');
     expect(component.state('popupVisible')).toEqual(false);
   });

   it('Updates search input', () => {
     const evt = {
       target: {
         value: 'png',
       },
     };
     component.find('.FileBrowser__input').simulate('change', evt);
     expect(component.state('search')).toEqual('png');
   });


   it('Sorts by az', () => {
     component.find('.FileBrowser__header--name').simulate('click');
     expect(component.state('sort')).toEqual('az');
   });

   it('Sorts by size', () => {
     component.find('.FileBrowser__header--size').simulate('click');
     expect(component.state('sort')).toEqual('size');
   });

   it('Sorts by modified', () => {
     component.find('.FileBrowser__header--date').simulate('click');
     expect(component.state('sort')).toEqual('modified');
   });

});
