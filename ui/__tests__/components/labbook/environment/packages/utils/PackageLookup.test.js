
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import PackageLookup from 'Components/labbook/environment/packages/utils/PackageLookup';

      test('Test PackageLookup', () => {
        const wrapper = renderer.create(<PackageLookup />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });
