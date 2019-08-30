// @flow
// vendor
import React, { Component } from 'react';
// mutations
import ConfigureDatasetMutation from 'Mutations/ConfigureDatasetMutation';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// components
import Modal from 'Components/common/Modal';
import ButtonLoader from 'Components/common/ButtonLoader';


class ConfigureModal extends Component {
  state = {
    buttonState: '',
    configValues: new Map(),
    configModalVisible: !this.props.dataset.backendIsConfigured,
    latestError: '',
  }

  /**
    @param {}
    redirect back to dataset listing
  */
  _handleRedirect = () => {
    const { history } = this.props;
    history.push('/datasets/local');
  }

  /**
    @param {}
    cancels confirm on configure dataset
  */
  _confirmCancelConfigure = () => {
    this.setState({ confirmMessage: '', buttonState: '' });
  }

  /**
    @param {Event} evt
    @param {String} parameter
    @param {String} parameterType
    updates configstate with input
  */
  _setDatasetConfig = (evt, parameter, parameterType) => {
    const { configValues } = this.state;
    const input = (parameterType === 'str')
      ? evt.target.value
      : evt.target.checked;
    const newConfig = configValues;

    if (input) {
      newConfig.set(parameter, input);
    } else {
      newConfig.delete(parameter);
    }
    this.setState({ configValues: newConfig });
  }


  /**
   * handles response from ConfigureDatasetMutation
   * @param {Object} response
   * @param {Object} error
   * @return {}
  */
  _configureDatasetCallback = (response, error, confirm) => {
    const configureDataset = response && response.configureDataset;

    if (error) {
      console.log(error);
      this.setState({ buttonState: 'error' });

      setTimeout(() => {
        this.setState({ buttonState: '' });
      }, 2000);

    } else if (configureDataset.errorMessage) {

      setErrorMessage('Failed to configure Dataset', [{ message: configureDataset.errorMessage }]);

      this.setState({
        buttonState: 'error',
        latestError: configureDataset.errorMessage,
      });

      setTimeout(() => {
        this.setState({ buttonState: '' });
      }, 2000);

    } else if (configureDataset.isConfigured
        && !configureDataset.shouldConfirm
        && !configureDataset.backgroundJobKey) {

      this._configureDataset(true);

    } else if (configureDataset.isConfigured
        && configureDataset.shouldConfirm
        && !confirm) {

      this.setState({ confirmMessage: configureDataset.confirmMessage });

    } else if (confirm) {
      this.setState({ buttonState: 'finished' });

      this.closeModal = setTimeout(() => {
        this.setState({
          configModalVisible: false,
          buttonState: '',
        });
      }, 2000);
    }
  }

  /**
   * @param {Boolean} confirm
    calls configure dataset mutation
  */
  _configureDataset = (confirm = null) => {
    const { configValues } = this.state;
    const { dataset } = this.props;
    const { labbookName, owner } = store.getState().routes;
    const successCall = () => {};
    const failureCall = () => {
      if (this.closeModal) {
        clearTimeout(this.closeModal);
        this.setState({ buttonState: '' });
      } else {
        this.setState({
          configModalVisible: true,
          buttonState: '',
          });
      }
    };
    const parameters = dataset.backendConfiguration.map(({ parameter, parameterType }) => {
      const value = configValues.get(parameter) || '';
      return {
        parameter,
        parameterType,
        value,
      };
    });

    this.setState({ buttonState: 'loading', latestError: '' });

    ConfigureDatasetMutation(
      owner,
      labbookName,
      parameters,
      confirm,
      successCall,
      failureCall,
      this._configureDatasetCallback,
    );
  }

  render() {
    const { state } = this;
    const someFieldsFilled = (this.state.configValues.size > 0);

    return (
      <Modal
        header="Configure Dataset"
        size="large"
        renderContent={() => (
          <div className="Dataset__config-modal">
            { state.confirmMessage
              && (
                <Modal
                  size="small"
                  renderContent={() => (
                    <div>
                      {state.confirmMessage}
                      <div className="Dataset__confirm-buttons">
                        <button
                          type="button"
                          onClick={() => this._confirmCancelConfigure()}
                          className="Btn--flat"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => this._configureDataset(true)}
                        >
                          Confirm
                        </button>
                      </div>
                    </div>
                  )}
                />
              )
            }
            <p>This dataset needs to be configured before it is ready for use.</p>

            {
              this.state.latestError
              && <p className="Dataset__config-error">{this.state.latestError}</p>
            }

            <div className="Dataset__config-container">
              <div className="Dataset__configs">
                {
                  dataset.backendConfiguration.map(({
                    description,
                    parameter,
                    parameterType,
                  }) => (
                    <div
                      className="Dataset__config-section"
                      key={parameter}
                    >
                      <div className="Dataset__config-parameter">
                        {parameter}
                        { (parameterType === 'bool')
                          && (
                            <input
                              type="checkbox"
                              onClick={evt => this._setDatasetConfig(evt, parameter, parameterType)}
                            />
                          )
                        }
                      </div>
                      <div className="Dataset__config-description">{description}</div>
                      { (parameterType === 'str')
                        && (
                          <input
                            type="text"
                            className="Dataset__config-textInput"
                            onKeyUp={(evt) => { this._setDatasetConfig(evt, parameter, parameterType); }}
                            onChange={(evt) => { this._setDatasetConfig(evt, parameter, parameterType); }}
                          />
                        )
                      }
                    </div>
                  ))
                }
              </div>
              <div className="Dataset__config-buttons">
                <button
                  type="button"
                  onClick={() => this._handleRedirect()}
                  className="Btn--flat"
                >
                  Return to Datasets
                </button>
                <ButtonLoader
                  buttonState={this.state.buttonState}
                  buttonText="Save Configuration"
                  className=""
                  params={{}}
                  buttonDisabled={!someFieldsFilled}
                  clicked={() => this._configureDataset()}
                />
              </div>
            </div>
          </div>
        )}
      />
    );
  }
}

export default ConfigureModal;
