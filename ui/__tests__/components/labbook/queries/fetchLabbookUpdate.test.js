
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import fetchLabbookUpdate from 'Components/labbook/queries/fetchLabbookUpdate';

      test('Test fetchLabbookUpdate', () => {
        const wrapper = renderer.create(<fetchLabbookUpdate />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });