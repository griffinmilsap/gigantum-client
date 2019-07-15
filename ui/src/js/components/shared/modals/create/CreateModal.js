// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// mutations
import CreateLabbookMutation from 'Mutations/CreateLabbookMutation';
import CreateDatasetMutation from 'Mutations/CreateDatasetMutation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// components
import Loader from 'Components/common/Loader';
import Modal from 'Components/common/Modal';
import CreateLabbook from './CreateLabbook';
import SelectBase from './SelectBase';
import CreateNav from './CreateNav';
// assets
import './CreateModal.scss';

/**
  @param {string} name
  @param {owner} name
  builds docker iamge of labbook
*/
const buildImage = (name, owner) => {
  BuildImageMutation(
    owner,
    name,
    false,
    (response, error) => {
      if (error) {
        console.error(error);
        setErrorMessage(`ERROR: Failed to build ${name}`, error);
      }
    },
  );
};

export default class CreateModal extends Component {
  state = {
    name: '',
    description: '',
    repository: '',
    componentId: '',
    revision: '',
    modalVisible: false,
    selectedComponentId: 'createLabbook',
    continueDisabled: true,
    modalBlur: false,
    createLabbookButtonState: '',
  };

  /**
    @param {Object, string} evt,field
    updates text in a state object and passes object to setState method
  */
  _updateTextState = (evt, field) => {
    const state = {};
    state[field] = evt.target.value;
    this.setState(state);
  }


  /**
    @param {}
    shows modal window by update component state
  */
  _showModal = () => {
    this.setState({
      modalVisible: true,
      selectedComponentId: 'createLabbook',
    });
  }

  /**
    @param {}
    hides modal window by update component state
  */
  _hideModal = () => {
    this.setState({ modalVisible: false });
  }

  /**
    @param {string} componentId
    sets view for child components using and id
  */
  _setComponent = (componentId) => {
    this.setState({ selectedComponentId: componentId });
  }

  /**
    @param {boolean} isDisabled
    setsContinueDisabled value to true or false
  */
  _toggleDisabledContinue = (isDisabled) => {
    this.setState({ continueDisabled: isDisabled });
  }

  /**
    @param { boolean} isSkip
    gets selected id and triggers continueSave function using refs
  */
  _continueSave = ({ isSkip, text }) => {
    const { props, state } = this;
    const componentId = state.selectedComponentId;

    if (props.datasets) {
      this[componentId].continueSave(isSkip);
    } else {
      this[componentId].continueSave(isSkip);
      this.setState({ continueDisabled: true });
      if (text === 'Create Labbook') {
        this.setState({ modalBlur: true });
      }
    }
  }

  /**
    @param {string} name
    @param {string} description
    sets name and description to state for create labbook mutation
  */
  _createLabbookCallback = (name, description) => {
    const { props } = this;

    this.setState({
      name,
      description,
    }, () => {
      if (props.datasets) {
        this._toggleDisabledContinue(true);
        this._createDatasetMutation();
      }
    });

    if (!props.datasets) {
      this._setComponent('selectBase');
    }
  }

  /**
    @param {Object} node
    @param {Object:String} node.componentId
    @param {Object:Int} node.revision
    @param {Object:String} node.repository,
    @param {Object:String} node.storageType,
    sets (repository, componentId and revision to state for create labbook mutation
  */
  _selectBaseCallback = (node) => {
    const { props } = this;
    const {
      repository,
      componentId,
      revision,
      storageType,
    } = node;
    const selectedType = props.datasets ? storageType : componentId;

    this.setState({
      repository,
      componentId: selectedType,
      revision,
    });
  }

  /**
    @param {String} createLabbookButtonState
    sets button state
  */
  _setButtonState = (createLabbookButtonState) => {
    this.setState({ createLabbookButtonState });
  }

  /**
      @param {}
      sets name and description to state for create labbook mutation
  */
  _createLabbookMutation = () => {
    const self = this;
    const {
      name,
      description,
      repository,
      componentId,
      revision,
    } = this.state;

    this.setState({
      createLabbookButtonState: 'loading',
      modalVisible: false,
    });

    document.getElementById('modal__cover').classList.remove('hidden');
    document.getElementById('loader').classList.remove('hidden');

    CreateLabbookMutation(
      name,
      description,
      repository,
      componentId,
      revision,
      (response, error) => {
        if (error) {
          setErrorMessage(`An error occured while trying to create Project '${name}'.`, error);
          document.getElementById('modal__cover').classList.add('hidden');
          document.getElementById('loader').classList.add('hidden');
          this.setState({
            modalBlur: false,
            createLabbookButtonState: 'error',
          });

          setTimeout(() => {
            this.setState({
              createLabbookButtonState: '',
            });
          }, 2000);
        } else {
          const { owner, name } = response.createLabbook.labbook;
          localStorage.setItem('latest_base', componentId);
          this.setState({
            createLabbookButtonState: 'finished',
          });

          setTimeout(() => {
            buildImage(name, owner);

            this.setState({
              createLabbookButtonState: '',
            }, () => {
              self.props.history.push(`../projects/${owner}/${name}`);
              document.getElementById('modal__cover').classList.add('hidden');
              document.getElementById('loader').classList.add('hidden');
            });
          }, 2000);
        }
      },
    );
  }

  /**
      @param {}
      sets name and description to state for create labbook mutation
  */
  _createDatasetMutation = () => {
    const self = this;
    const {
      name,
      description,
    } = this.state;

    this.setState({
      createLabbookButtonState: 'loading',
    });

    CreateDatasetMutation(
      name,
      description,
      'gigantum_object_v1',
      (response, error) => {
        if (error) {
          setErrorMessage(`An error occured while trying to create Dataset '${name}'.`, error);
          this.setState({
            modalBlur: false,
            createLabbookButtonState: 'error',
          });

          setTimeout(() => {
            this.setState({
              createLabbookButtonState: '',
            });
          }, 2000);
        } else {
          const { owner } = response.createDataset.dataset;

          this.setState({
            createLabbookButtonState: 'finished',
          });

          setTimeout(() => {
            this.setState({
              createLabbookButtonState: '',
            }, () => {
              self.props.history.push(`../datasets/${owner}/${name}`);
            });
          }, 2000);
        }
      },
    );
  }

  /**
   * @param {} -
   * selects current component to display in the create modal
   * @return {}
   */
  _currentComponent = () => {
    const { props, state } = this;
    switch (state.selectedComponentId) {
      case 'createLabbook':
        return {
          component:
            (<CreateLabbook
              ref={(ref) => { this.createLabbook = ref; }}
              createLabbookCallback={this._createLabbookCallback}
              toggleDisabledContinue={this._toggleDisabledContinue}
              setButtonState={this._setButtonState}
              history={props.history}
              hideModal={this._hideModal}
              auth={props.auth}
              datasets={props.datasets}
            />),
          header: props.datasets ? 'Create Dataset' : 'Create Project',
        };

      case 'selectBase':
        return {
          component:
          (<SelectBase
            ref={(ref) => { this.selectBase = ref; }}
            selectBaseCallback={this._selectBaseCallback}
            toggleDisabledContinue={this._toggleDisabledContinue}
            createLabbookMutation={this._createLabbookMutation}
            createDatasetMutation={this._createDatasetMutation}
            datasets={props.datasets}
          />),
          header: props.datasets ? 'Select A Type' : 'Select A Base',
          preHeader: props.datasets ? 'Create Dataset' : 'Create Project',
        };
      default:
        return {
          component:
          (<CreateLabbook
            ref={(ref) => { this.createLabbook = ref; }}
            createLabbookCallback={this._createLabbookCallback}
            toggleDisabledContinue={this._toggleDisabledContinue}
            setButtonState={this._setButtonState}
            history={props.history}
            hideModal={this._hideModal}
            auth={props.auth}
          />),
          header: 'Create Project',
        };
    }
  }

  render() {
    const { props, state } = this;
    const currentComponent = this._currentComponent();
    const modalBody = currentComponent.component;
    const modalSize = ((currentComponent.header === 'Select A Type')
      || (currentComponent.header === 'Select A Base'))
      ? 'large-long'
      : 'large';
    // declare css
    const loaderCSS = classNames({
      hidden: !state.modalBlur,
    });

    return (
      <div>
        { state.modalVisible
          && (
            <Modal
              size={modalSize}
              icon="add"
              handleClose={() => this._hideModal()}
              header={currentComponent.header}
              preHeader={currentComponent.preHeader}
              noPadding
              renderContent={() => (
                <div className="CreateModal">

                  { modalBody }

                  <CreateNav
                    self={this}
                    createLabbookButtonState={state.createLabbookButtonState}
                    selectedComponentId={state.selectedComponentId}
                    continueDisabled={state.continueDisabled}
                    setComponent={this._setComponent}
                    hideModal={this._hideModal}
                    continueSave={this._continueSave}
                    isDataset={props.datasets}
                  />
                </div>
              )}
            />
          )
        }

        { state.modalBlur && <Loader className={loaderCSS} /> }
      </div>
    );
  }
}
