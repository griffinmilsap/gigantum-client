// vendor
import React from 'react';
import renderer from 'react-test-renderer';
import { mount } from 'enzyme';
import relayTestingUtils from '@gigantum/relay-testing-utils';
// data
import codeData from 'Tests/components/labbook/code/__relaydata__/CodeBrowser.json';
// components
import ActionsMenu from 'Components/shared/fileBrowser/fileRow/ActionsMenu';

let edge = codeData.data.labbook.code.allFiles.edges[1]

const mutationData = {
  owner: 'uitest',
  labbookName: 'ui-test-project',
  section: 'code',
  connection: 'CodeBrowser_allFiles',
  favoriteConnection: 'CodeFavorite_favorites',
  parentId: codeData.data.labbook.id,
};

let file = {
  edge,
};

const fixtures = {
  closeLinkModal: jest.fn(),
  togglePopup: jest.fn(),
  addFolderVisible: jest.fn(),
  renameEditMode: jest.fn(),
  edge,
  mutationData,
  mutations: {
    moveLabbookFile: jest.fn(),
  },
  fileData: file,
  folder: false,
};


describe('ActionsMenu Component', () => {
  it('Renders a snapshot', () => {
    const wrapper = renderer.create(
      <ActionsMenu
        {...fixtures}
      />,
    );

    const tree = wrapper.toJSON();

    expect(tree).toMatchSnapshot();
  });
});
