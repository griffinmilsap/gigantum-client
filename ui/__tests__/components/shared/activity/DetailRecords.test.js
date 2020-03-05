// vendor
import React from 'react';
import renderer from 'react-test-renderer';
import { mount } from 'enzyme';
import relayTestingUtils from '@gigantum/relay-testing-utils';
// components
import DetailRecords from 'Components/shared/activity/wrappers/card/DetailRecords';
// data
import json from './__relaydata__/DetailRecords.json';


let fixtures = {
  keys: [],
  sectionType: 'labbook',
};

global.data['DetailRecordsQuery'] = json.data

describe('DetailRecords', () => {
  it('Renders a snapshot', () => {
    const wrapper = renderer.create(relayTestingUtils.relayWrap(
       <DetailRecords {...fixtures} />, {}, json.data.labbook)
    );

    const tree = wrapper.toJSON();

    expect(tree).toMatchSnapshot();
  });
});
