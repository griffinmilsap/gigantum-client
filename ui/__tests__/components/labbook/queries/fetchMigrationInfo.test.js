
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from '@gigantum/relay-testing-utils';
      // components;
      import fetchMigrationInfo from 'Components/labbook/queries/fetchMigrationInfo';

      test('Test fetchMigrationInfo', () => {
        const wrapper = renderer.create(<fetchMigrationInfo />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });