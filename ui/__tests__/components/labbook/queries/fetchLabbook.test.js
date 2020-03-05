
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import fetchLabbook from 'Components/labbook/queries/fetchLabbook';

      test('Test fetchLabbook', () => {
        const wrapper = renderer.create(<fetchLabbook />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });