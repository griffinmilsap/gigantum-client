
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import Secrets from 'Components/labbook/environment/secrets/Secrets';

      test('Test Secrets', () => {
        const wrapper = renderer.create(<Secrets />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });