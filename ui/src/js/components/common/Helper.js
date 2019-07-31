import React, { Component, Fragment } from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
// store
import {
  setHelperVisibility,
  setResizeHelper,
} from 'JS/redux/actions/helper';
import { setHelperVisible } from 'JS/redux/actions/footer';
// assets
import './Helper.scss';


class Helper extends Component {
  state = {
    helperMenuOpen: false,
    showPopup: false,
  };

  /**
    * @param {}
    * subscribe to store to update state
  */
  componentDidMount() {
    const { props } = this;
    window.addEventListener('resize', this._resize);

    props.auth.isAuthenticated().then((response) => {
      const guideShown = localStorage.getItem('guideShown');
      if (!guideShown && response) {
        this.setState({ showPopup: true });
        localStorage.setItem('guideShown', true);
        this._toggleIsVisible();
        this._toggleMenuView();
      }
    });
  }

  /**
    * @param {}
    * update store
  */
  _toggleIsVisible = () => {
    const { props } = this;
    props.setHelperVisibility(!props.isVisible);
  }

  /**
    * @param {}
    * toggles menu view
  */
  _toggleMenuView = () => {
    const { state } = this;
    setHelperVisible(!state.helperMenuOpen);
    this.setState({ helperMenuOpen: !state.helperMenuOpen });
  }

  /**
    * @param {}
    * update store to risize component
  */
  _resize = () => {
    const { props } = this;
    props.setResizeHelper();
  }

  render() {
    const { props, state } = this;
    // declare css here
    const menuCSS = classNames({
      Helper__menu: state.helperMenuOpen,
      hidden: !state.helperMenuOpen,
      'Helper__men--footer-open': props.footerVisible,
    });
    const helperButtonCSS = classNames({
      Helper__button: true,
      'Helper__button--open': state.helperMenuOpen,
      'Helper__button--bottom': props.uploadOpen && !state.helperMenuOpen,
    });

    return (
      <div className="Helper">
        { state.showPopup
        && (
          <Fragment>
            <div className="Helper__prompt">
              <div>
                <p>Use the guide to view tips on how to use Gigantum. The guide can be toggled in the Help menu below.</p>
              </div>

              <div>
                <button
                  type="button"
                  className="button--green"
                  onClick={() => this.setState({ showPopup: false })}
                >
                  Got it!
                </button>
              </div>
            </div>
            <div className="Helper__prompt-pointer" />
          </Fragment>
        )
        }

        <div
          className={helperButtonCSS}
          onClick={() => this._toggleMenuView()}
        />

        <div className={menuCSS}>
          <div
            className="Helper__menu-feedback"
            onClick={() => window.open('https://feedback.gigantum.com')}
          >
            <h5>Feedback</h5>
            <div className="Helper__feedback-button" />
          </div>
          <div
            className="Helper__menu-discussion"
            onClick={() => window.open('https://spectrum.chat/gigantum')}
          >
            <h5>Discuss</h5>
            <div
              className="Helper__discussion-button"
            />
          </div>
          <div
            className="Helper__menu-docs"
            onClick={() => window.open('https://docs.gigantum.com/docs')}
          >
            <h5>Docs</h5>
            <div className="Helper__docs-button" />
          </div>

          <div className="Helper__menu-guide">
            <h5>Guide</h5>
            <label
              htmlFor="guideShown"
              className="Helper-guide-switch"
            >
              <input
                id="guideShown"
                type="checkbox"
                defaultChecked={!localStorage.getItem('guideShown')}
                onClick={() => this._toggleIsVisible()}
              />
              <span className="Helper-guide-slider" />
            </label>
          </div>
        </div>
      </div>
    );
  }
}


const mapStateToProps = state => ({
  resize: state.helper.resize,
  isVisible: state.helper.isVisible,
  footerVisible: state.helper.footerVisible,
  uploadOpen: state.footer.uploadOpen,
});

const mapDispatchToProps = dispatch => ({
  setHelperVisibility,
  setResizeHelper,
});

export default connect(mapStateToProps, mapDispatchToProps)(Helper);
