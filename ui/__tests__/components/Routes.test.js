import Routes from 'Components/Routes';
import history from 'JS/history';

import React from 'react';
// import toJson from 'enzyme-to-json';
import { mount, shallow } from 'Enzyme';
import Auth from 'JS/Auth/Auth';
import renderer from 'react-test-renderer';
import relayTestingUtils from '@gigantum/relay-testing-utils';
import { MemoryRouter } from 'react-router';

const variables = { first: 20, owner: 'uitest', name: 'ui-test-labbook' };

test('Test Routes Rendering', () => {
  const auth = new Auth();
  auth.isAuthenticated = () => true;
  auth.login = () => true;
  auth.logout = () => true;

  const component = renderer.create(
    relayTestingUtils.relayWrap(<Routes />, {}, config.data),
  );
  let tree = component.toJSON();

  expect(tree).toMatchSnapshot();
});


describe('Test Routes View Change', () => {
  const auth = new Auth();
  auth.isAuthenticated = () => true;
  auth.login = () => true;
  auth.logout = () => true;

  const component = shallow(<Routes />);

  it('renders header routes', () => {
    component.find('.Header__nav-item').at(0).simulate('click');
    expect(component).toMatchSnapshot();
  });

  it('renders header routes', () => {
    component.find('.Header__nav-item').at(1).simulate('click');
    expect(component).toMatchSnapshot();
  });
});


describe('Test Router', () => {
  const auth = new Auth();
  auth.isAuthenticated = () => true;
  auth.login = () => true;
  auth.logout = () => true;

  const component = mount(
    <MemoryRouter initialEntries={['/labbooks/']}>
      <Routes
        history={history}
      />
    </MemoryRouter>,
  );

  it('check history props is labbook', () => {
    expect(component.node.history.location.pathname === '/labbooks/').toBeTruthy();
  });


  it('check history props is datasets', () => {
    component.node.history.replace('/datasets/');
    expect(component.node.history.location.pathname === '/datasets/').toBeTruthy();
  });

  // if('test datasets snapshot'){
  //   expect(component.node).toMatchSnapshot();
  // }
});


describe('Test Labbooks routes', () => {
  const auth = new Auth();
  auth.isAuthenticated = () => true;
  auth.login = () => true;
  auth.logout = () => true;


  it('with data', () => {
    const component = shallow(
      <MemoryRouter initialEntries={[`/labbooks/${variables.name}/`]}>
        <Routes
          history={history}
        />
      </MemoryRouter>,
    );
    expect(component).toMatchSnapshot();
  });

  it('without data', () => {
    const component = shallow(
      <MemoryRouter initialEntries={[`/labbooks/${variables.name}/`]}>
        <Routes
          history={history}
        />
      </MemoryRouter>,
    );

    expect(component).toMatchSnapshot();
  });

  it('test callback', () => {
    const component = shallow(
      <MemoryRouter initialEntries={['/callback']}>
        <Routes
          history={history}
        />
      </MemoryRouter>,
    );

    expect(component).toMatchSnapshot();
  });
});

export default variables;
