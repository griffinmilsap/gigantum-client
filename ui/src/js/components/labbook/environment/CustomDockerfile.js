// vendor
import React, { Component, Fragment } from 'react';
import ReactMarkdown from 'react-markdown';
import classNames from 'classnames';
// Components
import CodeBlock from 'Components/labbook/renderers/CodeBlock';
import Tooltip from 'Components/common/Tooltip';
// mutations
import AddCustomDockerMutation from 'Mutations/AddCustomDockerMutation';
// store
import store from 'JS/redux/store';
import { setContainerMenuWarningMessage } from 'JS/redux/actions/labbook/environment/environment';
// config
import { setErrorMessage, setWarningMessage } from 'JS/redux/actions/footer';
import config from 'JS/config';
// assets
import './CustomDockerfile.scss';

export default class CustomDockerfile extends Component {
  constructor(props) {
    super(props);
    this.state = {
      originalDockerfile: this.props.dockerfile,
      dockerfileContent: this.props.dockerfile,
      lastSavedDockerfileContent: this.props.dockerfile,
      editingDockerfile: false,
      savingDockerfile: false,
    };
  }

  static getDerivedStateFromProps(props, state) {
    if (props.dockerfile !== state.originalDockerfile) {
      return {
        ...state,
        originalDockerfile: props.dockerfile,
        dockerfileContent: props.dockerfile,
        lastSavedDockerfileContent: props.dockerfile,
      };
    }
    return state;
  }

  /**
  *  @param {}
  *  updates docker file
  *  @return {}
  */
  _saveDockerfile() {
    const { props, state } = this;


    const { status } = store.getState().containerStatus;


    const canEditEnvironment = config.containerStatus.canEditEnvironment(status) && !props.isLocked;


    const { owner, labbookName } = store.getState().routes;

    if (navigator.onLine) {
      if (canEditEnvironment) {
        const validDictionary = new Set(['LABEL', 'RUN', 'ENV', '#']);
        const splitDockerSnippet = this.state.dockerfileContent.split(/\n|\\n/);
        let valid = true;
        splitDockerSnippet.forEach((snippetLine, index) => {
          const firstVal = snippetLine.split(' ')[0];
          const previousLine = splitDockerSnippet[index - 1] && splitDockerSnippet[index - 1];
          let isPreviousLineExtended = false;

          if (previousLine) {
            const strippedSpaces = previousLine.split(' ').join('');
            isPreviousLineExtended = strippedSpaces[strippedSpaces.length - 1] === '\\';
          }

          if ((firstVal.length && !validDictionary.has(firstVal.toUpperCase()) && firstVal[0] !== '#') && !isPreviousLineExtended) {
            valid = false;
          }
        });

        if (valid) {
          this.setState({ savingDockerfile: true });

          AddCustomDockerMutation(
            owner,
            labbookName,
            this.state.dockerfileContent,
            (res, error) => {
              if (error) {
                console.log(error);
                setErrorMessage('Dockerfile was not set: ', error);
                this.setState({ savingDockerfile: false });
              } else {
                props.buildCallback();
                this.setState({ editingDockerfile: false, lastSavedDockerfileContent: this.state.dockerfileContent, savingDockerfile: false });
              }
            },
          );
        } else {
          setWarningMessage('Invalid command entered. Commands must begin with: LABEL, RUN, ENV, or #');
        }
      } else {
        setContainerMenuWarningMessage('Stop Project before editing the environment. \n Be sure to save your changes.');
      }
    } else {
      setErrorMessage('Cannot remove package at this time.', [{ message: 'An internet connection is required to modify the environment.' }]);
    }
  }

  /**
  *  @param {}
  *  sets constainer to edit mode if user can edit environment.
  *  @return {}
  */
  _editDockerfile() {
    const { status } = store.getState().containerStatus;
    const canEditEnvironment = config.containerStatus.canEditEnvironment(status) && !this.props.isLocked;
    if (canEditEnvironment) {
      this.setState({ editingDockerfile: true });
    } else {
      setContainerMenuWarningMessage('Stop Project before editing the environment. \n Be sure to save your changes.');
    }
  }


  render() {
    const { props, state } = this;


    const dockerfileCSS = classNames({
      'column-1-span-11': true,
      empty: !this.state.dockerfileContent,
    });


    const editDockerfileButtonCSS = classNames({
      'Btn Btn--feature Btn--feature Btn__edit Btn__edit--featurePosition absolute--important': true,
      hidden: state.editingDockerfile,
      'Tooltip-data': props.isLocked,
    });


    const renderedContent = state.dockerfileContent ? `\`\`\`\n${state.dockerfileContent}\n\`\`\`` : 'No commands provided.';

    return (
      <div className="CustomDockerfile">

        <div className="Environment__headerContainer">

          <h4>
            Custom Docker Instructions
            <Tooltip section="dockerInstructionsEnvironment" />
          </h4>

        </div>

        <div className="CustomDockerfile__sub-header">

          <p>Add commands below to modify your environment. Note: Docker instructions are executed after packages are installed.</p>

          <div className="CustomDockerfile--code-snippet flex">
            <p>For example, to install a pip package from a Github repo add:</p>
            <code>RUN pip install git+https://git.repo/some_pkg.git</code>
          </div>

        </div>
        <div className="grid">
          <div className="CustomDockerfile__content Card Card--auto Card--no-hover column-1-span-12">
            <button
              className={editDockerfileButtonCSS}
              data-tooltip="Container must be turned off to edit docker snippets"
              onClick={() => this._editDockerfile()}
            >
              <span>Edit Dockerfile</span>
            </button>
            {
              this.state.editingDockerfile

                ? (
                  <Fragment>

                    <textarea
                      className="CustomDockerfile__textarea"
                      type="text"
                      onChange={(evt) => { this.setState({ dockerfileContent: evt.target.value }); }}
                      placeholder="Enter dockerfile commands here"
                      defaultValue={state.dockerfileContent ? state.dockerfileContent : ''}
                    />

                    <div className="CustomDockerfile__buttonContainer">

                      <div className="column-1-span-2">

                        <button
                          onClick={() => this.setState({ editingDockerfile: false, dockerfileContent: state.lastSavedDockerfileContent })}
                          className="CustomDockerfile__content-cancel-button Btn--flat"
                        >
                      Cancel
                        </button>

                        <button
                          disabled={state.savingDockerfile}
                          onClick={() => this._saveDockerfile()}
                          className="CustomDockerfile__content-save-button"
                        >
                      Save
                        </button>

                      </div>

                    </div>

                  </Fragment>
                )

                : (
                  <Fragment>

                    <div className={dockerfileCSS}>

                      <ReactMarkdown
                        renderers={{ code: props => <CodeBlock {...props} language="dockerfile" /> }}
                        className="ReactMarkdown"
                        source={renderedContent}
                      />

                    </div>

                  </Fragment>
                )
            }

          </div>
        </div>
      </div>
    );
  }
}
