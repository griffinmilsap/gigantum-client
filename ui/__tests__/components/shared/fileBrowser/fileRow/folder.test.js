// vendor
import React from 'react';
import renderer from 'react-test-renderer';
import { mount } from 'enzyme';
import relayTestingUtils from '@gigantum/relay-testing-utils';
import path from 'path';
// data
import codeData from 'Tests/components/labbook/code/__relaydata__/CodeBrowser.json';
// components
import Folder from 'Components/shared/fileBrowser/fileRow/Folder';


let edge = codeData.data.labbook.code.allFiles.edges[0];
let fileEdge = codeData.data.labbook.code.allFiles.edges[1];
let filename = path.basename(edge.node.key);
let file = {
  edge,
  children: {
    [fileEdge.node.key]: fileEdge,
  },
};

const mutationData = {
  owner: 'uitest',
  labbookName: 'ui-test-project',
  section: 'code',
  connection: 'CodeBrowser_allFiles',
  favoriteConnection: 'CodeFavorite_favorites',
  parentId: codeData.data.labbook.id,
};

const fixtures = {
  connectDragSource: jsx => jsx,
  connectDropTarget: jsx => jsx,
  closeLinkModal: jest.fn(),
  checkLocal: jest.fn(),
  setState: jest.fn(),
  updateChildState: jest.fn(),
  codeDirUpload: jest.fn(),
  setParentDragFalse: jest.fn(),
  isSelected: true,
  filename,
  key: file.edge.node.key,
  multiSelect: false,
  mutationData,
  fileData: file,
  mutations: {
    moveLabbookFile: jest.fn(),
  },
  sort: 'all',
  reverse: true,
  childrenState: {
    [edge.node.key]: {
      isExpanded: false,
      isSelected: false,
      isIncomplete: false,
      isAddingFolder: false,
    },
  },
  section: 'code',
};

describe('File component', () => {

  it('File Snapshot', () => {
    const component = renderer.create(
       <Folder.DecoratedComponent {...fixtures}/>
    );
    const tree = component.toJSON();

    expect(tree).toMatchSnapshot();
  });

  const component = mount(
     <Folder.DecoratedComponent {...fixtures}/>
  );

  it('Test rename', () => {
    const evt = {
      target: {
        value: 'NewFileName.js',
      },
    };
    component.find('.Btn__rename').simulate('click');
    component.find('.File__input').simulate('change', evt);
    expect(component.state('renameValue')).toEqual(evt.target.value);
  });

  it('Test cancel rename', () => {
    component.find('.File__input--rename-cancel').simulate('click');
    expect(component.state('renameValue')).toEqual(fixtures.filename);
  });


  it('Test rename add', () => {
    const evt = {
      target: {
        value: 'NewFileName.js',
      },
    };
    component.find('.Btn__rename').simulate('click');
    component.find('.File__input').simulate('change', evt);
    component.find('.File__input--rename-add').simulate('click');
    expect(fixtures.mutations.moveLabbookFile.mock.calls.length).toEqual(1);
  });
});
