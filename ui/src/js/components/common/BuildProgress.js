// vendor
import React, { Component, Fragment } from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
import ReactTooltip from 'react-tooltip';
// store
import { setBuildingState } from 'JS/redux/actions/labbook/labbook';
// mutations
import CancelBuildMutation from 'Mutations/container/CancelBuildMutation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// assets
import './BuildProgress.scss';

/**
  @param {Boolean} noisCompletede
  @param {Boolean} error
  @param {Boolean} cancelingBuild
  determines what the subtext should be
*/
const getSubText = (isComplete, error, cancelingBuild) => {
  let subText = 'Applying changes and rebuilding Project environment...';
  subText = isComplete ? 'Environment Build Successful' : subText;
  subText = error ? 'Environment Build Failed' : subText;
  subText = cancelingBuild ? 'Build Canceled' : subText;
  return subText;
};


class BuildProgress extends Component {
  state = {
    showBuild: this.props.keepOpen,
    cancelingBuild: false,
  }

  /** *
  * @param {}
  * sets mounted to true for component
  */
  componentDidMount() {
    this.mounted = true;
  }

  /** *
  * @param {}
  * sets mounted to false for component
  */
  componentWillUnmount() {
    this.mounted = false;
  }

  /**
  *  @param {Boolean} showBuild
  *  sets entry method state
  */
  _setShowbuild = (showBuild) => {
    this.setState({ showBuild });
  }

  /**
  *  @param {}
  *  fires build cancelation
  */
  _cancelBuild = () => {
    const { props } = this;
    const { owner, name } = props;
    const callback = () => {
      setTimeout(() => {
        setBuildingState(owner, name, false);
      }, 3000);
    };

    setBuildingState(owner, name, true);
    this.setState({ cancelingBuild: true });
    CancelBuildMutation(
      props.owner,
      props.name,
      callback,
    );
  }


  /**
  *  @param {}
  *  fires build cancelation
  */
  _noCacheRebuild = () => {
    const {
      owner,
      name,
      toggleModal,
    } = this.props;
    const callback = () => {};

    setBuildingState(owner, name, true);
    this.setState({ cancelingBuild: true });
    BuildImageMutation(
      owner,
      name,
      { noCache: true },
      callback,
    );
    toggleModal(false);
  }

  /**
    @param {}
    gets percentage for progress
  */
  _getPercentageComplete = () => {
    const { props } = this;
    const { buildId, messageStackHistory } = props;
    const footerMessage = messageStackHistory.filter(message => message.id === buildId);

    if (footerMessage[0] && footerMessage[0].messageBody) {
      const { status } = footerMessage[0];
      const { message } = footerMessage[0].messageBody[0];
      const regex = /(Step [0-9]+\/[0-9]+)/g;
      const percentRegex = /[0-9]+\/[0-9]+/;
      const matches = message.match(regex);
      const lastMatchPct = matches ? matches[matches.length - 1].match(percentRegex)[0].split('/') : [];
      const { error } = footerMessage[0];

      const regexMessage = message.replace(regex, '<span style="color:#fcd430">$1</span>')
          // Backspace (note funny syntax) deletes any previous character
          .replace(/.[\b]/g, '')
          // \r\n should be treated as a regular newline
          .replace(/\r\n/g, '\n')
          // Get rid of anything on a line before a carriage return
          // Using a group because Firefox still doesn't support ES2018 negative look-behind
          .replace(/(\n|^)[^\n]*\r/g, '$1');

      if (
        ((process.env.BUILD_TYPE === 'cloud') && !props.keepOpen && (status === 'finished'))
        || ((lastMatchPct[0] === lastMatchPct[1]) && !props.keepOpen && matches)
      ) {
        setTimeout(() => {
          if (this.mounted) {
            props.toggleModal(false);
          }
        }, 2000);
      }

      return {
        percentageComplete: matches ? `${Math.round((lastMatchPct[0] / lastMatchPct[1]) * 100)}%` : '',
        message: regexMessage,
        isComplete: matches && (lastMatchPct[0] === lastMatchPct[1]),
        error,
      };
    }
    return {
      percentageComplete: '',
      message: '',
      error: false,
    };
  }

  render() {
    const { props, state } = this;
    const {
      percentageComplete,
      message,
      isComplete,
      error,
    } = this._getPercentageComplete();
    const buildButtonText = state.showBuild ? 'Back' : 'View Build Output';
    const subText = getSubText(isComplete, error, state.cancelingBuild);
    let { headerText } = props;
    headerText = ((isComplete || state.cancelingBuild || error) && state.showBuild)
      ? subText : headerText;
    // decalre css here
    const headerCSS = classNames({
      'BuildProgress__header-text': true,
      'BuildProgress__header-text--completed': isComplete && state.showBuild,
      'BuildProgress__header-text--failed': (state.cancelingBuild || error) && state.showBuild,
    });
    const progressCSS = classNames({
      BuildProgress__progress: true,
      'BuildProgress__progress--completed': isComplete,
      'BuildProgress__progress--failed': state.cancelingBuild || error,
    });
    const progressTextCSS = classNames({
      BuildProgress__text: true,
      'BuildProgress__text--completed': isComplete,
      'BuildProgress__text--failed': state.cancelingBuild || error,
    });

    return (
      <div className="BuildProgress">
        <div className="BuildProgress__header">
          <h4 className={headerCSS}>{headerText}</h4>
        </div>
        {
          state.showBuild
          && (
            <div
              className="BuildProgress__output"
            >
              <div dangerouslySetInnerHTML={{ __html: message }} />
            </div>
          )
        }
        {
          !state.showBuild
          && (
            <div className="BuildProgress__body flex flex--column align-items--center">
              <p className="BuildProgress__close-text">
                Close this window to continue using Gigantum while your environment is building.
              </p>
              <div className={progressCSS}>
                {percentageComplete}
              </div>
              <p className={progressTextCSS}>
                {subText}
              </p>
            </div>
          )
        }

        <div className="BuildProgress__buttons flex justify--right">
          {
          !props.keepOpen
          && (
          <Fragment>
            <button
              className="Btn Btn--flat margin-right--auto"
              type="button"
              disabled={message.length === 0}
              onClick={() => this._setShowbuild(!state.showBuild)}
            >
              {buildButtonText}
            </button>
            <button
              className="Btn Btn--inverted align-self--end"
              type="button"
              disabled={isComplete || state.cancelingBuild}
              onClick={() => this._cancelBuild()}
            >
              Cancel Build
            </button>
          </Fragment>
          )
          }
          {
            error
            && (
            <Fragment>
              <button
                className="Btn--inverted align-self--end"
                type="button"
                onClick={() => this._noCacheRebuild()}
                data-tip="This will attempt to rebuild the container from the beginning without using Docker's cache"
                data-for="Tooltip--noCache"
              >
                Clear Cache & Build
              </button>
              <ReactTooltip
                place="top"
                id="Tooltip--noCache"
                delayShow={500}
              />
            </Fragment>
            )
          }
          <button
            className="align-self--end"
            type="button"
            onClick={() => props.toggleModal(false)}
          >
            Close
          </button>
        </div>
      </div>
    );
  }
}

const mapStateToProps = state => state.footer;

const mapDispatchToProps = () => ({});

export default connect(mapStateToProps, mapDispatchToProps)(BuildProgress);
