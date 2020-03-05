
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import InputBrowser from 'Components/labbook/inputData/InputBrowser';

      test('Test InputBrowser', () => {
        const wrapper = renderer.create(<InputBrowser />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });