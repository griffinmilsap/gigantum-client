
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import { mount } from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import LabbookRefetch from 'Components/labbook/LabbookRefetch';

      test('Test LabbookRefetch', () => {
        const wrapper = renderer.create(<LabbookRefetch />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });
