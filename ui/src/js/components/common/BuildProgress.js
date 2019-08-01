// vendor
import React, { Component, Fragment } from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
// store
import { setBuildingState } from 'JS/redux/actions/labbook/labbook';
// mutations
import CancelBuildMutation from 'Mutations/container/CancelBuildMutation';
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
    const callback = () => {
      setTimeout(() => {
        setBuildingState(false);
      }, 3000);
    };

    setBuildingState(true);
    this.setState({ cancelingBuild: true });
    CancelBuildMutation(
      props.owner,
      props.name,
      callback,
    );
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
      const { message } = footerMessage[0].messageBody[0];
      const regex = /(Step [0-9]+\/[0-9]+)/g;
      const percentRegex = /[0-9]+\/[0-9]+/;
      const matches = message.match(regex);
      const lastMatchPct = matches ? matches[matches.length - 1].match(percentRegex)[0].split('/') : [];
      const { error } = footerMessage[0];

      if ((lastMatchPct[0] === lastMatchPct[1]) && !props.keepOpen && matches) {
        setTimeout(() => {
          if (this.mounted) {
            props.toggleModal(false);
          }
        }, 2000);
      }

      return {
        percentageComplete: matches ? `${Math.round((lastMatchPct[0] / lastMatchPct[1]) * 100)}%` : '',
        message: message.replace(regex, '<span style="color:#fcd430">$1</span>'),
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
    const buildButtonText = state.showBuild ? 'Back' : 'View Build Ouput';
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
