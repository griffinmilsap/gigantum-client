// vendor
import React from 'react';
import renderer from 'react-test-renderer';
import { mount } from 'enzyme';
import relayTestingUtils from '@gigantum/relay-testing-utils';
// components;
import MostRecentInput from 'Components/labbook/inputData/MostRecentInput';

test('Test MostRecentInput', () => {
  const wrapper = renderer.create(<MostRecentInput />);

  const tree = wrapper.toJSON();

  expect(tree).toMatchSnapshot();
});
