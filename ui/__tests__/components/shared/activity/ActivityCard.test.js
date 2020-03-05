// vendor
import React, { Component } from 'react';
import renderer from 'react-test-renderer';
import { mount } from 'enzyme';
import relayTestingUtils from '@gigantum/relay-testing-utils';
import { Provider } from 'react-redux';
// components
import ActivityCard from 'Components/shared/activity/wrappers/card/ActivityCard';
// Data
import json from 'Tests/components/labbook/__relaydata__/LabbookContainerQuery.json';
// store
import store from 'JS/redux/store';

let { labbook } = json.data;

let fixtures = {
  sectionType: 'labbook',
  isFirstCard: true,
  addCluster: jest.fn(),
  compressExpanded: jest.fn(),
  isCompressed: false,
  isExpandedHead: true,
  isExpandedEnd: true,
  isExpandedNode: true,
  attachedCluster: false,
  collapsed: false,
  clusterObject: {},
  position: 0,
  hoveredRollback: true,
  key: 'ActivityCard',
  edge: labbook.activityRecords.edges[0],
};


describe('Activity', () => {
  it('renders a snapshot', () => {

    const wrapper = renderer.create(<ActivityCard {...fixtures} />);

    const tree = wrapper.toJSON();

    expect(tree).toMatchSnapshot();
  });
});
