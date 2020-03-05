
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import Packages from 'Components/labbook/environment/packages/Packages';

      test('Test Packages', () => {
        const wrapper = renderer.create(<Packages />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });