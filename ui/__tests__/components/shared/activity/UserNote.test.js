// vendor
import React from 'react'
import renderer from 'react-test-renderer';
import { mount } from 'enzyme'
import relayTestingUtils from '@gigantum/relay-testing-utils'
// components
import UserNote from 'Components/shared/activity/date/note/UserNote';


describe('UserNote', () => {
  it('Renders a snapshot', () => {
    const wrapper = renderer.create(<UserNote />);

    const tree = wrapper.toJSON();

    expect(tree).toMatchSnapshot();
  });

});
