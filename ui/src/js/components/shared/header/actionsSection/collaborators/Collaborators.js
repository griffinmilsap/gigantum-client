// @flow
// vendor
import { QueryRenderer, graphql } from 'react-relay';
import React, { Component } from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
// environment
import environment from 'JS/createRelayEnvironment';
// store
import store from 'JS/redux/store';
import { setCollaborators, setCanManageCollaborators } from 'JS/redux/actions/shared/collaborators/collaborators';
// components
import CollaboratorsModal from './modal/CollaboratorsModal';
// assets
import './Collaborators.scss';

export const CollaboratorsQuery = graphql`
  query CollaboratorsQuery($name: String!, $owner: String!){
    labbook(name: $name, owner: $owner){
      collaborators {
        id
        owner
        name
        collaboratorUsername
        permission
      }
      canManageCollaborators
    }
  }`;

export const CollaboratorsDatasetQuery = graphql`
query CollaboratorsDatasetQuery($name: String!, $owner: String!){
  dataset(name: $name, owner: $owner){
    collaborators {
      id
      owner
      name
      collaboratorUsername
      permission
    }
    canManageCollaborators
  }
}`;

/**
* @param {Array<Object>} collaborators
* @param {string} owner
* returns  a fitered list of collaborators
* @return {Array}
*/
const getCollaboratorFiltered = (collaborators, owner) => collaborators
  && collaborators.filter(
    ({ collaboratorUsername }) => collaboratorUsername !== owner,
  ).map(
    ({ collaboratorUsername }) => collaboratorUsername,
  );

type Props = {
  auth: {
    renewToken: Function,
  },
  sectionType: string,
  showLoginPrompt: Function,
}

class CollaboratorButton extends Component<Props> {
  state = {
    collaboratorModalVisible: false,
    canClickCollaborators: false,
    sessionValid: false,
  };

  static getDerivedStateFromProps(nextProps, nextState) {
    if (nextProps.menuOpen) {
      return nextProps.checkSessionIsValid().then((res) => {
        if (res.data && res.data.userIdentity && res.data.userIdentity.isSessionValid) {
          return {
            ...nextState,
            sessionValid: true,
          };
        }
        return {
          ...nextState,
          sessionValid: false,
        };
      });
    }
    return nextState;
  }

  /**
  *  @param {Function} retry
  *  shows hide collaborators modal
  *  @return {}
  */
  _toggleCollaborators = (retry) => {
    const { auth, showLoginPrompt } = this.props;
    const { sessionValid, collaboratorModalVisible } = this.state;

    if (navigator.onLine) {
      if (sessionValid) {
        this.setState({ collaboratorModalVisible: !collaboratorModalVisible });
      } else {
        auth.renewToken(true, () => {
          showLoginPrompt();
        }, () => {
          if (retry) {
            retry();
          }
          this.setState({ collaboratorModalVisible: !collaboratorModalVisible });
        });
      }
    } else {
      showLoginPrompt();
    }
  }

  /**
  *  @param {Array} collaborators
  *  @param {Array} collaboratorFilteredArr
  *  gets list of collaborators
  *  @return {}
  */
  _getCollaboratorList = (collaborators, collaboratorFilteredArr) => {
    let lastParsedIndex;
    let collaboratorSubText = collaboratorFilteredArr ? collaboratorFilteredArr.join(', ') : '';

    if (collaboratorSubText.length > 18 && collaboratorSubText.length) {
      collaboratorSubText = collaboratorSubText.slice(0, 18);

      lastParsedIndex = collaboratorSubText.split(', ').length - 1;

      const lastParsed = collaboratorSubText.split(', ')[lastParsedIndex];

      if (collaborators[lastParsedIndex] !== lastParsed) {
        lastParsedIndex -= 1;

        collaboratorSubText = collaboratorSubText.split(', ');
        collaboratorSubText.pop();
        collaboratorSubText = collaboratorSubText.join(', ');
      }
      const collaboratorLength = collaboratorFilteredArr.length - lastParsedIndex - 1;
      collaboratorSubText += `...+${collaboratorLength}`;
    }
    return collaboratorSubText;
  }

  /**
  *  @param {String} name
  *  gets info for a collaborator
  *  @return {}
  */
  _getCollabororInfo = (name) => {
    let { collaborators, canManageCollaborators } = store.getState().collaborators;
    collaborators = collaborators && (collaborators[name] || null);
    canManageCollaborators = canManageCollaborators && (canManageCollaborators[name] || null);
    return { collaborators, canManageCollaborators };
  }

  render() {
    const self = this;
    const {
      collaboratorModalVisible,
    } = this.state;
    const {
      showLoginPrompt,
      sectionType,
    } = this.props;
    // either labbook or dataset
    // get section from props

    const { name, owner } = this.props[sectionType];
    const query = (sectionType === 'dataset') ? CollaboratorsDatasetQuery : CollaboratorsQuery;
    const { collaborators, canManageCollaborators } = this._getCollabororInfo(name);

    return (
      <QueryRenderer
        query={query}
        environment={environment}
        variables={{
          name,
          owner,
        }}
        render={(response) => {
          const { props } = response;

          if (props) {
            const section = (sectionType === 'dataset')
              ? props.dataset
              : props.labbook;
            const collaboratorFilteredArr = getCollaboratorFiltered(section.collaborators, owner);
            const collaboratorNames = self._getCollaboratorList(
              section.collaborators,
              collaboratorFilteredArr,
            );

            this.canManageCollaborators = section.canManageCollaborators;
            this.collaborators = section.collaborators;

            setCollaborators({ [name]: this.collaborators });
            setCanManageCollaborators({ [name]: this.canManageCollaborators });
            // declare css here
            const collaboratorButtonCSS = classNames({
              'Collaborators__btn Btn--flat Btn--no-underline': true,
            });
            const collaboratorCSS = classNames({
              Collaborators: true,
            });

            return (

              <div className={collaboratorCSS}>
                <button
                  type="button"
                  onClick={() => this._toggleCollaborators(response.retry)}
                  className={collaboratorButtonCSS}
                >
                      Collaborators
                  <p className="BranchMenu__collaborator-names">{collaboratorNames}</p>

                  { (collaboratorNames.length === 0)
                    && (
                      <p>
                        Click to add
                      </p>
                    )
                  }
                </button>

                { collaboratorModalVisible
                    && (
                    <CollaboratorsModal
                      sectionType={sectionType}
                      key="CollaboratorsModal"
                      collaborators={section.collaborators}
                      owner={owner}
                      name={name}
                      toggleCollaborators={this._toggleCollaborators}
                      canManageCollaborators={section.canManageCollaborators}
                    />
                    )

                }
              </div>
            );
          } if (collaborators !== null) {
            const collaboratorFilteredArr = getCollaboratorFiltered(collaborators, owner);
            const collaboratorNames = self._getCollaboratorList(
              collaborators,
              collaboratorFilteredArr,
            );

            // declare css here
            const collaboratorButtonCSS = classNames({
              Collaborators__btn: true,
              'Btn--flat': true,
            });
            const collaboratorCSS = classNames({
              Collaborators: true,
            });

            return (

              <div className={collaboratorCSS}>
                <button
                  type="button"
                  onClick={() => this._toggleCollaborators()}
                  className={collaboratorButtonCSS}
                >
                  Collaborators
                  <p className="BranchMenu__collaborator-names">{collaboratorNames}</p>
                </button>

                { collaboratorModalVisible
                  && (
                    <CollaboratorsModal
                      key="CollaboratorsModal"
                      collaborators={collaborators}
                      canManageCollaborators={canManageCollaborators}
                      owner={owner}
                      labbookName={name}
                      toggleCollaborators={this._toggleCollaborators}
                    />
                  )
                 }
              </div>
            );
          }
          return (
            <div className="Collaborators disabled">
              <button
                type="button"
                onClick={() => showLoginPrompt()}
                className="Collaborators__btn Btn--flat disabled"
              >
                Collaborators
              </button>
            </div>
          );
        }}
      />

    );
  }
}

const mapStateToProps = () => ({});

const mapDispatchToProps = () => ({
  setCollaborators,
  setCanManageCollaborators,
});

export default connect(mapStateToProps, mapDispatchToProps)(CollaboratorButton);
