
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import { mount } from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import OutputBrowser from 'Components/labbook/outputData/OutputBrowser';

      test('Test OutputBrowser', () => {
        const wrapper = renderer.create(<OutputBrowser />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });
