
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import MostRecentCode from 'Components/labbook/code/MostRecentCode';

      test('Test MostRecentCode', () => {
        const wrapper = renderer.create(<MostRecentCode />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });