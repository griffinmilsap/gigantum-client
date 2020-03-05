// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { createFragmentContainer, graphql } from 'react-relay';
// mutations
import ChangeLabbookBaseMutation from 'Mutations/environment/ChangeLabbookBaseMutation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// store
import { setErrorMessage, setInfoMessage } from 'JS/redux/actions/footer';
// components
import PackageCount from 'Components/labbook/overview/PackageCount';
import Loader from 'Components/common/Loader';
import SelectBaseModal from 'Components/shared/modals/SelectBaseModal';
// assets
import './Base.scss';

/**
*  @param {Boolean} isLocked
*  @param {Boolean} upToDate
*  returns tooltip
*  @return {Object}
*/
const getTooltip = (isLocked, upToDate) => {
  const defaultTooltip = isLocked ? 'Cannot modify environment while Project is in use' : '';
  const upToDateTooltip = upToDate ? 'Base is up to date' : defaultTooltip;
  return {
    upToDateTooltip,
    defaultTooltip,
  };
};

/**
    @param {name, owner}
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
        setErrorMessage(owner, name, `ERROR: Failed to build ${name}`, error);
      }
    },
  );
};


type Props = {
  environment: {
    base: Object,
  },
  isLocked: bool,
  baseLatestRevision: string,
  overview: Object,
  owner: string,
  name: string,
};

class Base extends Component<Props> {
  state = {
    baseModalVisible: false,
    forceUpdateDisabled: false,
  }

  /**
      @param {}
      update base mutation
  */
  _updateBaseMutation = () => {
    const { props } = this;
    const {
      owner,
      name,
      baseLatestRevision,
    } = props;
    const {
      repository,
      componentId,
    } = props.environment.base;

    this.setState({ forceUpdateDisabled: true });

    ChangeLabbookBaseMutation(
      owner,
      name,
      repository,
      componentId,
      baseLatestRevision,
      (response, error) => {
        this.setState({ forceUpdateDisabled: false });
        if (error) {
          setErrorMessage(owner, name, 'An error occurred while trying to change bases.', error);
        } else {
          setInfoMessage(owner, name, 'Updated Base successfully. Rebuilding environment. Please wait...');
          buildImage(name, owner);
        }
      },
    );
  }

  /**
    @param {boolean} baseModalVisible
    sets baseModalVisible value to true or false
  */
  _toggleBaseModal = (baseModalVisible) => {
    this.setState({ baseModalVisible });
  }

  render() {
    const { state } = this;
    const {
      environment,
      isLocked,
      baseLatestRevision,
      overview,
      owner,
      name,
    } = this.props;
    const { base } = environment;
    const isUpToDate = baseLatestRevision === base.revision;
    const { defaultTooltip, upToDateTooltip } = getTooltip(isLocked, isUpToDate);
    const disableUpdateButton = isUpToDate || isLocked || state.forceUpdateDisabled;
    // declare css here
    const changeButtonCSS = classNames({
      'Btn Btn__base Btn__base--change Btn--action': true,
      'Tooltip-data Tooltip-data--auto': isLocked,
    });
    const updateButtonCSS = classNames({
      'Btn Btn__base Btn__base--update Btn--action': true,
      'Tooltip-data Tooltip-data--auto': (isUpToDate || isLocked) && !state.forceUpdateDisabled,
      'Btn__base--loading': state.forceUpdateDisabled,

    });
    if (base) {
      return (
        <div className="Base">
          <div className="Base__info grid">
            <div className="Base__card Card--auto Card--no-hover column-1-span-12">

              <div className="Base__imageContainer">
                <img
                  className="Base__image"
                  height="35"
                  width="35"
                  src={base.icon}
                  alt={base.name}
                />

                <div className="Base__title">
                  <h6 className="Base__name">{base.name}</h6>
                  <p className="Base__revision">{`Revision: ${base.revision}`}</p>
                  <p className="Base__paragraph">{base.description}</p>
                </div>

              </div>

              <div className="Base__languages">
                <h6 className="bold">Languages</h6>
                <ul>
                  {
                    base.languages.map(language => (
                      <li key={`${language}_language`}>{language}</li>
                    ))
                  }
                </ul>
              </div>

              <div className="Base__tools">
                <h6 className="bold">Tools</h6>
                <ul>
                  {
                    base.developmentTools && base.developmentTools.map(tool => (
                      <li key={`${tool}_tool`}>{tool}</li>
                    ))
                  }
                </ul>
              </div>

              {
                (overview) && <PackageCount overview={overview} />
              }
              {
                state.baseModalVisible
                && (
                <SelectBaseModal
                  owner={owner}
                  name={name}
                  toggleModal={() => this._toggleBaseModal(false)}
                />
                )
              }
              {
                !overview
                && (
                <div className="Base__actions flex flex--column justify--center">
                  <button
                    className={changeButtonCSS}
                    type="button"
                    data-tooltip={defaultTooltip}
                    disabled={isLocked}
                    onClick={() => this._toggleBaseModal(true)}
                  >
                    Change
                  </button>
                  <button
                    className={updateButtonCSS}
                    data-tooltip={upToDateTooltip}
                    disabled={disableUpdateButton}
                    onClick={() => this._updateBaseMutation()}
                    type="button"
                  >
                    Update
                  </button>
                </div>
                )
              }

            </div>

          </div>

        </div>
      );
    }
    return (
      <Loader />
    );
  }
}

export default createFragmentContainer(
  Base,
  {
    environment: graphql`fragment Base_environment on Environment {
    base{
      id
      schema
      repository
      componentId
      revision
      name
      description
      readme
      tags
      icon
      osClass
      osRelease
      license
      url
      revision
      languages
      developmentTools
      packageManagers
      dockerImageServer
      dockerImageNamespace
      dockerImageRepository
      dockerImageTag
    }
  }`,
  },
);
