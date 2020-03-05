// vendor
import React from 'react';
import renderer from 'react-test-renderer';
import { mount } from 'enzyme';
import path from 'path';
// data
import codeData from 'Tests/components/labbook/code/__relaydata__/CodeBrowser.json';
// components
import File from 'Components/shared/fileBrowser/fileRow/File';

const edge = codeData.data.labbook.code.allFiles.edges[1];
const filename = path.basename(edge.node.key);
const file = {
  edge,
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
  },
  sort: 'all',
  reverse: true,
  childrenState: {},
  section: 'code',
  isDragging: false,
};

describe('Project File component', () => {
  it('File Snapshot', () => {
    const component = renderer.create(
      <File.DecoratedComponent {...fixtures} />,
    );

    const tree = component.toJSON();

    expect(tree).toMatchSnapshot();
  });

  const component = mount(
    <File.DecoratedComponent {...fixtures} />,
  );

  it('Rename', () => {
    const evt = {
      target: {
        value: 'NewFileName.js',
      },
    };
    component.find('.Btn__rename').simulate('click');
    component.find('.File__input').simulate('change', evt);
    expect(component.state('newFileName')).toEqual(evt.target.value);
  });

  it('Cancel rename', () => {
    component.find('.File__btn--rename-cancel').simulate('click');
    expect(component.state('newFileName')).toEqual(fixtures.filename);
  });


  it('Rename add', () => {
    const evt = {
      target: {
        value: 'NewFileName.js',
      },
    };
    component.find('.Btn__rename').simulate('click');
    component.find('.File__input').simulate('change', evt);
    component.find('.File__btn--rename-add').simulate('click');
    expect(fixtures.mutations.moveLabbookFile.mock.calls.length).toEqual(1);
  });

  it('Mouseover file row', () => {
    const evt = {
      preventDefault: () => {},
    };
    component.find('.File').simulate('mouseover', evt);
    expect(component.state('hover')).toEqual(true);
  });


  it('Mouseout file row', () => {
    const evt = {
      preventDefault: () => {},
    };
    component.find('.File').simulate('mouseout', evt);
    expect(component.state('hover')).toEqual(false);
  });

  it('MouseEnter', () => {
    const evt = {
      preventDefault: () => {},
    };
    component.setProps({ isDragging: true });
    component.setState({ isDragging: true, isHovered: true });
    component.find('.File').simulate('mouseEnter', evt);
    expect(component.state('isDragging')).toEqual(true);
  });


  it('MouseLeave', () => {
    const evt = {
      preventDefault: () => {},
    };
    component.setProps({ isDragging: false });
    component.setState({ isDragging: false, isHovered: false });
    component.find('.File').simulate('mouseLeave', evt);
    expect(component.state('isDragging')).toEqual(false);
  });

  it('Set File to unchecked', () => {
    const evt = {
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    component.find('.CheckboxMultiselect__check').simulate('click', evt);
    expect(component.state('isSelected')).toEqual(false);
  });

  it('Set File to checked', () => {
    const evt = {
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    component.find('.CheckboxMultiselect__uncheck').simulate('click', evt);
    expect(component.state('isSelected')).toEqual(true);
  });
});
