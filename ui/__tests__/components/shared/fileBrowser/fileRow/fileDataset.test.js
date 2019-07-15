// vendor
import React from 'react';
import renderer from 'react-test-renderer';
import { mount } from 'enzyme';
import relayTestingUtils from '@gigantum/relay-testing-utils';
import path from 'path';
// data
import codeData from 'Tests/components/labbook/code/__relaydata__/CodeBrowser.json';
// components
import File from 'Components/shared/fileBrowser/fileRow/File';
import UserIdentity from 'JS/Auth/UserIdentity';

jest.mock('JS/Auth/UserIdentity', () => {
    return {
      getUserIdentity: jest.fn().mockResolvedValue({
        data: {
          userIdentity: {
            isSessionValid: true,
         },
       },
     }),
   }
 });


let edge = codeData.data.labbook.code.allFiles.edges[0];
edge.node.isDatasetRoot = true;
edge.node.isLocal = false;
let filename = path.basename(edge.node.key);
let file = {
  edge,
};

const mutationData = {
  owner: 'uitest',
  labbookName: 'ui-test-project',
  section: 'data',
  connection: 'CodeBrowser_allFiles',
  favoriteConnection: 'CodeFavorite_favorites',
  parentId: codeData.data.labbook.id,
};

let fixtures = {
  connectDragSource: jsx => jsx,
  closeLinkModal: jest.fn(),
  setState: jest.fn(),
  updateChildState: jest.fn(),
  codeDirUpload: jest.fn(),
  isSelected: true,
  filename,
  key: file.edge.node.key,
  multiSelect: false,
  mutationData,
  fileData: file,
  mutations: {
    moveLabbookFile: jest.fn(),
    downloadDatasetFiles: jest.fn(),
  },
  sort: 'all',
  reverse: true,
  childrenState: {},
  section: 'data',
  isDragging: false,
  isParent: true,
};


describe('Dataset File component', () => {
  it('File Snapshot', () => {
    const component = renderer.create(<File.DecoratedComponent {...fixtures}/>);

    const tree = component.toJSON();

    expect(tree).toMatchSnapshot();
  });

  const component = mount(<File.DecoratedComponent {...fixtures}/>);
});
