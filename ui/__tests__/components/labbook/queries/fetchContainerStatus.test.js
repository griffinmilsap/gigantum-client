
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import fetchContainerStatus from 'Components/labbook/queries/fetchContainerStatus';

      test('Test fetchContainerStatus', () => {
        const wrapper = renderer.create(<fetchContainerStatus />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });